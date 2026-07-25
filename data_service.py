"""
Graphico Pro — Data Service
Handles CSV/JSON file processing, cleaning, merging, splitting, editing,
plot generation (Plotly), and instant PDF report generation.
"""

import json
import logging
import io
import csv
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

import pandas as pd

from config.settings import (
    UPLOAD_DIRECTORY,
    EXPORT_DIRECTORY,
    MAX_UPLOAD_SIZE_BYTES,
)
from config.constants import (
    HttpStatus,
    ApiMessage,
    ErrorCode,
    MIME_TYPES,
)
from backend.utils import (
    generate_id,
    get_timestamp,
    sanitize_filename,
    get_file_extension,
    get_mime_type,
    humanize_bytes,
    ensure_directory,
    success_response,
    error_response,
    logger as utils_logger,
)

logger = logging.getLogger(__name__)


class DataService:
    """
    Processes uploaded data files: CSV, JSON.
    Provides cleaning, merging, splitting, editing, plotting, and PDF report generation.
    """

    def __init__(self):
        self.upload_dir = UPLOAD_DIRECTORY
        self.export_dir = EXPORT_DIRECTORY
        ensure_directory(self.upload_dir)
        ensure_directory(self.export_dir)

    # ------------------------------------------------------------------------
    # LOAD
    # ------------------------------------------------------------------------

    def load_dataframe(self, file_path: str) -> Tuple[Optional[pd.DataFrame], Optional[Tuple]]:
        """
        Load a CSV or JSON file into a pandas DataFrame.

        Args:
            file_path: Absolute path to the data file

        Returns:
            Tuple of (DataFrame, error_response)
        """
        try:
            path = Path(file_path).resolve()
            if not path.exists():
                return None, error_response(
                    message="File not found",
                    error_code=ErrorCode.FILE_NOT_FOUND,
                    status_code=HttpStatus.NOT_FOUND,
                )

            ext = path.suffix.lower()

            if ext == ".csv":
                df = pd.read_csv(path)
            elif ext == ".json":
                df = pd.read_json(path)
            else:
                return None, error_response(
                    message=f"Unsupported data format: {ext}",
                    error_code=ErrorCode.FILE_UNSUPPORTED_TYPE,
                    status_code=HttpStatus.BAD_REQUEST,
                )

            return df, None

        except Exception as e:
            logger.error(f"Failed to load dataframe: {e}", exc_info=True)
            return None, error_response(
                message="Failed to load data file",
                error_code=ErrorCode.FILE_CORRUPTED,
                status_code=HttpStatus.INTERNAL_SERVER_ERROR,
            )

    def get_preview(self, file_path: str, rows: int = 20) -> Tuple[Optional[Dict], Optional[Tuple]]:
        """
        Get a preview of the data file.

        Returns:
            Dict with columns, dtypes, row count, sample rows, and basic stats.
        """
        df, error = self.load_dataframe(file_path)
        if error:
            return None, error

        preview = {
            "columns": df.columns.tolist(),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "row_count": len(df),
            "sample_rows": df.head(rows).fillna("").to_dict(orient="records"),
            "null_counts": df.isnull().sum().to_dict(),
            "basic_stats": {},
        }

        # Numeric column stats
        numeric_cols = df.select_dtypes(include="number").columns
        if len(numeric_cols) > 0:
            stats_df = df[numeric_cols].describe()
            preview["basic_stats"] = stats_df.fillna(0).to_dict()

        return preview, None

    # ------------------------------------------------------------------------
    # CLEAN
    # ------------------------------------------------------------------------

    def clean_data(
        self,
        file_path: str,
        drop_duplicates: bool = True,
        fill_numeric: Optional[str] = "mean",
        drop_null_rows: bool = False,
        fill_categorical: Optional[str] = "mode",
    ) -> Tuple[Optional[str], Optional[Tuple]]:
        """
        Clean a data file and save the cleaned version.

        Returns:
            Tuple of (cleaned_file_path, error_response)
        """
        df, error = self.load_dataframe(file_path)
        if error:
            return None, error

        try:
            # Drop duplicates
            if drop_duplicates:
                df = df.drop_duplicates()

            # Fill numeric columns
            numeric_cols = df.select_dtypes(include="number").columns
            if fill_numeric == "mean":
                df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].mean())
            elif fill_numeric == "median":
                df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].median())
            elif fill_numeric == "zero":
                df[numeric_cols] = df[numeric_cols].fillna(0)

            # Fill categorical columns
            categorical_cols = df.select_dtypes(include="object").columns
            if fill_categorical == "mode":
                for col in categorical_cols:
                    if not df[col].mode().empty:
                        df[col] = df[col].fillna(df[col].mode()[0])

            # Drop remaining nulls if requested
            if drop_null_rows:
                df = df.dropna()

            return self._save_dataframe(df, file_path, "_cleaned"), None

        except Exception as e:
            logger.error(f"Data cleaning failed: {e}", exc_info=True)
            return None, error_response(
                message="Data cleaning failed",
                error_code=ErrorCode.SERVER_INTERNAL,
                status_code=HttpStatus.INTERNAL_SERVER_ERROR,
            )

    # ------------------------------------------------------------------------
    # MERGE
    # ------------------------------------------------------------------------

    def merge_files(
        self,
        file_path_1: str,
        file_path_2: str,
        on_column: str,
        how: str = "inner",
    ) -> Tuple[Optional[str], Optional[Tuple]]:
        """
        Merge two data files on a common column.

        Returns:
            Tuple of (merged_file_path, error_response)
        """
        df1, error = self.load_dataframe(file_path_1)
        if error:
            return None, error

        df2, error = self.load_dataframe(file_path_2)
        if error:
            return None, error

        if on_column not in df1.columns or on_column not in df2.columns:
            return None, error_response(
                message=f"Column '{on_column}' not found in both files",
                error_code=ErrorCode.VALIDATION_MISSING_FIELD,
                status_code=HttpStatus.BAD_REQUEST,
            )

        try:
            merged = pd.merge(df1, df2, on=on_column, how=how)
            return self._save_dataframe(merged, file_path_1, "_merged"), None
        except Exception as e:
            logger.error(f"Merge failed: {e}", exc_info=True)
            return None, error_response(
                message="File merge failed",
                error_code=ErrorCode.SERVER_INTERNAL,
                status_code=HttpStatus.INTERNAL_SERVER_ERROR,
            )

    # ------------------------------------------------------------------------
    # SPLIT
    # ------------------------------------------------------------------------

    def split_file(
        self,
        file_path: str,
        split_column: Optional[str] = None,
        num_splits: int = 2,
    ) -> Tuple[Optional[List[str]], Optional[Tuple]]:
        """
        Split a data file into multiple files.

        Args:
            split_column: Column to group by for splitting.
            num_splits: Number of row-based splits (if split_column is None).

        Returns:
            Tuple of (list_of_file_paths, error_response)
        """
        df, error = self.load_dataframe(file_path)
        if error:
            return None, error

        try:
            output_paths = []

            if split_column and split_column in df.columns:
                for group_value, group_df in df.groupby(split_column):
                    safe_name = sanitize_filename(str(group_value))
                    suffix = f"_split_{safe_name}"
                    path, _ = self._save_dataframe(group_df, file_path, suffix)
                    output_paths.append(path)
            else:
                chunk_size = max(1, len(df) // num_splits)
                for i in range(num_splits):
                    start = i * chunk_size
                    end = start + chunk_size if i < num_splits - 1 else len(df)
                    chunk = df.iloc[start:end]
                    suffix = f"_split_{i+1}"
                    path, _ = self._save_dataframe(chunk, file_path, suffix)
                    output_paths.append(path)

            return output_paths, None

        except Exception as e:
            logger.error(f"Split failed: {e}", exc_info=True)
            return None, error_response(
                message="File split failed",
                error_code=ErrorCode.SERVER_INTERNAL,
                status_code=HttpStatus.INTERNAL_SERVER_ERROR,
            )

    # ------------------------------------------------------------------------
    # EDIT CELL
    # ------------------------------------------------------------------------

    def edit_cell(
        self,
        file_path: str,
        row_index: int,
        column: str,
        new_value: str,
    ) -> Tuple[Optional[str], Optional[Tuple]]:
        """
        Edit a single cell value in the data file.

        Returns:
            Tuple of (updated_file_path, error_response)
        """
        df, error = self.load_dataframe(file_path)
        if error:
            return None, error

        if column not in df.columns:
            return None, error_response(
                message=f"Column '{column}' not found",
                error_code=ErrorCode.VALIDATION_MISSING_FIELD,
                status_code=HttpStatus.BAD_REQUEST,
            )

        if row_index < 0 or row_index >= len(df):
            return None, error_response(
                message=f"Row index {row_index} out of range",
                error_code=ErrorCode.VALIDATION_VALUE_OUT_OF_RANGE,
                status_code=HttpStatus.BAD_REQUEST,
            )

        try:
            df.at[row_index, column] = new_value
            return self._save_dataframe(df, file_path, "_edited"), None
        except Exception as e:
            logger.error(f"Cell edit failed: {e}", exc_info=True)
            return None, error_response(
                message="Cell edit failed",
                error_code=ErrorCode.SERVER_INTERNAL,
                status_code=HttpStatus.INTERNAL_SERVER_ERROR,
            )

    # ------------------------------------------------------------------------
    # ADD / DELETE ROWS & COLUMNS
    # ------------------------------------------------------------------------

    def add_row(self, file_path: str, row_data: Dict[str, Any]) -> Tuple[Optional[str], Optional[Tuple]]:
        """Add a new row to the data file."""
        df, error = self.load_dataframe(file_path)
        if error:
            return None, error

        try:
            df = pd.concat([df, pd.DataFrame([row_data])], ignore_index=True)
            return self._save_dataframe(df, file_path, "_updated"), None
        except Exception as e:
            logger.error(f"Add row failed: {e}", exc_info=True)
            return None, error_response(
                message="Failed to add row",
                error_code=ErrorCode.SERVER_INTERNAL,
                status_code=HttpStatus.INTERNAL_SERVER_ERROR,
            )

    def delete_row(self, file_path: str, row_index: int) -> Tuple[Optional[str], Optional[Tuple]]:
        """Delete a row by index."""
        df, error = self.load_dataframe(file_path)
        if error:
            return None, error

        if row_index < 0 or row_index >= len(df):
            return None, error_response(
                message=f"Row index {row_index} out of range",
                error_code=ErrorCode.VALIDATION_VALUE_OUT_OF_RANGE,
                status_code=HttpStatus.BAD_REQUEST,
            )

        try:
            df = df.drop(row_index).reset_index(drop=True)
            return self._save_dataframe(df, file_path, "_updated"), None
        except Exception as e:
            logger.error(f"Delete row failed: {e}", exc_info=True)
            return None, error_response(
                message="Failed to delete row",
                error_code=ErrorCode.SERVER_INTERNAL,
                status_code=HttpStatus.INTERNAL_SERVER_ERROR,
            )

    def add_column(self, file_path: str, column_name: str, default_value: Any = "") -> Tuple[Optional[str], Optional[Tuple]]:
        """Add a new column with an optional default value."""
        df, error = self.load_dataframe(file_path)
        if error:
            return None, error

        try:
            df[column_name] = default_value
            return self._save_dataframe(df, file_path, "_updated"), None
        except Exception as e:
            logger.error(f"Add column failed: {e}", exc_info=True)
            return None, error_response(
                message="Failed to add column",
                error_code=ErrorCode.SERVER_INTERNAL,
                status_code=HttpStatus.INTERNAL_SERVER_ERROR,
            )

    def delete_column(self, file_path: str, column_name: str) -> Tuple[Optional[str], Optional[Tuple]]:
        """Delete a column by name."""
        df, error = self.load_dataframe(file_path)
        if error:
            return None, error

        if column_name not in df.columns:
            return None, error_response(
                message=f"Column '{column_name}' not found",
                error_code=ErrorCode.VALIDATION_MISSING_FIELD,
                status_code=HttpStatus.BAD_REQUEST,
            )

        try:
            df = df.drop(columns=[column_name])
            return self._save_dataframe(df, file_path, "_updated"), None
        except Exception as e:
            logger.error(f"Delete column failed: {e}", exc_info=True)
            return None, error_response(
                message="Failed to delete column",
                error_code=ErrorCode.SERVER_INTERNAL,
                status_code=HttpStatus.INTERNAL_SERVER_ERROR,
            )

    # ------------------------------------------------------------------------
    # PLOT GENERATION (Plotly)
    # ------------------------------------------------------------------------

    def generate_plot(
        self,
        file_path: str,
        plot_type: str,
        x_column: Optional[str] = None,
        y_column: Optional[str] = None,
        title: str = "Graphico Pro — Plot",
    ) -> Tuple[Optional[str], Optional[Tuple]]:
        """
        Generate a Plotly plot as JSON for frontend rendering.

        Args:
            file_path: Path to data file
            plot_type: scatter | line | bar | histogram | box | pie | heatmap | area
            x_column: Column for X axis
            y_column: Column for Y axis
            title: Plot title

        Returns:
            Tuple of (plotly_json_string, error_response)
        """
        df, error = self.load_dataframe(file_path)
        if error:
            return None, error

        try:
            import plotly.graph_objects as go
            import plotly.express as px

            numeric_cols = df.select_dtypes(include="number").columns.tolist()

            if plot_type == "scatter":
                fig = px.scatter(df, x=x_column, y=y_column, title=title)
            elif plot_type == "line":
                fig = px.line(df, x=x_column, y=y_column, title=title)
            elif plot_type == "bar":
                fig = px.bar(df, x=x_column, y=y_column, title=title)
            elif plot_type == "histogram":
                fig = px.histogram(df, x=x_column or numeric_cols[0] if numeric_cols else None, title=title)
            elif plot_type == "box":
                fig = px.box(df, x=x_column, y=y_column, title=title)
            elif plot_type == "pie":
                fig = px.pie(df, names=x_column, values=y_column, title=title)
            elif plot_type == "heatmap":
                corr = df[numeric_cols].corr() if numeric_cols else df.corr()
                fig = px.imshow(corr, text_auto=True, title=title)
            elif plot_type == "area":
                fig = px.area(df, x=x_column, y=y_column, title=title)
            else:
                return None, error_response(
                    message=f"Unsupported plot type: {plot_type}",
                    error_code=ErrorCode.VALIDATION_INVALID_FORMAT,
                    status_code=HttpStatus.BAD_REQUEST,
                )

            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="#17181C",
                plot_bgcolor="#17181C",
                font_color="#EDEDEF",
                title_font_color="#C9A15B",
            )

            plot_json = fig.to_json()
            return plot_json, None

        except ImportError:
            return None, error_response(
                message="Plotly not installed. Run: pip install plotly",
                error_code=ErrorCode.SERVER_CONFIGURATION,
                status_code=HttpStatus.INTERNAL_SERVER_ERROR,
            )
        except Exception as e:
            logger.error(f"Plot generation failed: {e}", exc_info=True)
            return None, error_response(
                message="Plot generation failed",
                error_code=ErrorCode.SERVER_INTERNAL,
                status_code=HttpStatus.INTERNAL_SERVER_ERROR,
            )

    # ------------------------------------------------------------------------
    # PDF REPORT GENERATION
    # ------------------------------------------------------------------------

    def generate_report_pdf(
        self,
        file_path: str,
        user_id: str,
        include_plots: bool = True,
    ) -> Tuple[Optional[str], Optional[Tuple]]:
        """
        Generate an instant insights PDF report from a data file.

        Args:
            file_path: Path to data file
            user_id: User ID for export directory
            include_plots: Whether to embed plots in the report

        Returns:
            Tuple of (pdf_file_path, error_response)
        """
        df, error = self.load_dataframe(file_path)
        if error:
            return None, error

        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors
            from reportlab.lib.units import inch
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            user_export_dir = self.export_dir / user_id
            ensure_directory(user_export_dir)

            report_id = generate_id("report")
            output_path = user_export_dir / f"data_report_{report_id}.pdf"

            doc = SimpleDocTemplate(
                str(output_path),
                pagesize=A4,
                rightMargin=50,
                leftMargin=50,
                topMargin=50,
                bottomMargin=50,
            )

            styles = getSampleStyleSheet()
            title_style = styles["Heading1"]
            heading_style = styles["Heading2"]
            normal_style = styles["Normal"]
            story = []

            # Title
            story.append(Paragraph("Graphico Pro — Data Insights Report", title_style))
            story.append(Spacer(1, 0.2 * inch))
            story.append(Paragraph(f"Generated: {get_timestamp()}", normal_style))
            story.append(Spacer(1, 0.3 * inch))

            # Dataset overview
            story.append(Paragraph("Dataset Overview", heading_style))
            story.append(Paragraph(f"Rows: {len(df)}", normal_style))
            story.append(Paragraph(f"Columns: {len(df.columns)}", normal_style))
            story.append(Paragraph(f"Columns: {', '.join(df.columns.tolist())}", normal_style))
            story.append(Spacer(1, 0.2 * inch))

            # Missing values
            story.append(Paragraph("Missing Values", heading_style))
            nulls = df.isnull().sum()
            for col, count in nulls.items():
                if count > 0:
                    story.append(Paragraph(f"• {col}: {count} missing", normal_style))
            if nulls.sum() == 0:
                story.append(Paragraph("No missing values found.", normal_style))
            story.append(Spacer(1, 0.2 * inch))

            # Numeric stats
            numeric_df = df.describe()
            if len(numeric_df.columns) > 0:
                story.append(Paragraph("Numeric Column Statistics", heading_style))
                table_data = [["Column", "Mean", "Std", "Min", "Max"]]
                for col in numeric_df.columns:
                    table_data.append([
                        col,
                        f"{numeric_df[col]['mean']:.2f}",
                        f"{numeric_df[col]['std']:.2f}",
                        f"{numeric_df[col]['min']:.2f}",
                        f"{numeric_df[col]['max']:.2f}",
                    ])
                t = Table(table_data[:15])  # Limit to 15 cols
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#C9A15B")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#2A2C32")),
                ]))
                story.append(t)
                story.append(Spacer(1, 0.2 * inch))

            # Plots
            if include_plots:
                story.append(Paragraph("Visualizations", heading_style))
                numeric_cols = df.select_dtypes(include="number").columns[:5]

                # Histogram
                if len(numeric_cols) > 0:
                    fig, ax = plt.subplots(figsize=(6, 3))
                    ax.hist(df[numeric_cols[0]].dropna(), bins=20, color="#C9A15B", edgecolor="#2A2C32")
                    ax.set_title(f"Distribution: {numeric_cols[0]}", color="#EDEDEF")
                    ax.set_facecolor("#17181C")
                    fig.patch.set_facecolor("#17181C")
                    ax.tick_params(colors="#9A9CA5")
                    img_buffer = io.BytesIO()
                    fig.savefig(img_buffer, format="png", dpi=100, bbox_inches="tight")
                    plt.close(fig)
                    img_buffer.seek(0)
                    story.append(Image(img_buffer, width=450, height=225))
                    story.append(Spacer(1, 0.2 * inch))

                # Correlation heatmap (simple bar version)
                if len(numeric_cols) > 1:
                    fig, ax = plt.subplots(figsize=(6, 3))
                    corr = df[numeric_cols[:5]].corr()
                    cax = ax.matshow(corr, cmap="YlOrBr")
                    ax.set_xticks(range(len(corr.columns)))
                    ax.set_yticks(range(len(corr.columns)))
                    ax.set_xticklabels(corr.columns, rotation=45, ha="left", color="#9A9CA5", fontsize=7)
                    ax.set_yticklabels(corr.columns, color="#9A9CA5", fontsize=7)
                    ax.set_title("Correlation Matrix", color="#EDEDEF")
                    fig.patch.set_facecolor("#17181C")
                    ax.set_facecolor("#17181C")
                    img_buffer = io.BytesIO()
                    fig.savefig(img_buffer, format="png", dpi=100, bbox_inches="tight")
                    plt.close(fig)
                    img_buffer.seek(0)
                    story.append(Image(img_buffer, width=350, height=350))
                    story.append(Spacer(1, 0.2 * inch))

            # Build PDF
            doc.build(story)
            logger.info(f"PDF report generated: {output_path}")
            return str(output_path), None

        except ImportError as e:
            logger.error(f"Missing library: {e}")
            return None, error_response(
                message=f"Missing library: {e}. Install reportlab and matplotlib.",
                error_code=ErrorCode.SERVER_CONFIGURATION,
                status_code=HttpStatus.INTERNAL_SERVER_ERROR,
            )
        except Exception as e:
            logger.error(f"PDF report generation failed: {e}", exc_info=True)
            return None, error_response(
                message="PDF report generation failed",
                error_code=ErrorCode.SERVER_INTERNAL,
                status_code=HttpStatus.INTERNAL_SERVER_ERROR,
            )

    # ------------------------------------------------------------------------
    # EXPORT DATA
    # ------------------------------------------------------------------------

    def export_data(
        self,
        file_path: str,
        format: str,
        user_id: str,
    ) -> Tuple[Optional[str], Optional[Tuple]]:
        """
        Export data to specified format.

        Args:
            file_path: Source data file
            format: csv | json | xlsx | parquet
            user_id: User ID

        Returns:
            Tuple of (exported_file_path, error_response)
        """
        df, error = self.load_dataframe(file_path)
        if error:
            return None, error

        try:
            user_dir = self.export_dir / user_id
            ensure_directory(user_dir)

            export_id = generate_id("export")
            format = format.lower()

            if format == "csv":
                output_path = user_dir / f"data_{export_id}.csv"
                df.to_csv(output_path, index=False)
            elif format == "json":
                output_path = user_dir / f"data_{export_id}.json"
                df.to_json(output_path, orient="records", indent=2)
            elif format == "xlsx":
                output_path = user_dir / f"data_{export_id}.xlsx"
                df.to_excel(output_path, index=False)
            elif format == "parquet":
                output_path = user_dir / f"data_{export_id}.parquet"
                df.to_parquet(output_path, index=False)
            else:
                return None, error_response(
                    message=f"Unsupported export format: {format}",
                    error_code=ErrorCode.VALIDATION_INVALID_FORMAT,
                    status_code=HttpStatus.BAD_REQUEST,
                )

            logger.info(f"Data exported: {output_path}")
            return str(output_path), None

        except Exception as e:
            logger.error(f"Data export failed: {e}", exc_info=True)
            return None, error_response(
                message="Data export failed",
                error_code=ErrorCode.SERVER_INTERNAL,
                status_code=HttpStatus.INTERNAL_SERVER_ERROR,
            )

    # ------------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------------

    def _save_dataframe(self, df: pd.DataFrame, source_path: str, suffix: str) -> Tuple[str, None]:
        """Save a DataFrame to the same directory as the source file with a suffix."""
        source = Path(source_path)
        ext = source.suffix.lower()
        new_name = f"{source.stem}{suffix}{ext}"
        new_path = source.parent / new_name

        if ext == ".csv":
            df.to_csv(new_path, index=False)
        elif ext == ".json":
            df.to_json(new_path, orient="records", indent=2)

        logger.info(f"Data saved: {new_path}")
        return str(new_path)


# ----------------------------------------------------------------------------
# GLOBAL INSTANCE
# ----------------------------------------------------------------------------

_data_service_instance = None


def get_data_service() -> DataService:
    global _data_service_instance
    if _data_service_instance is None:
        _data_service_instance = DataService()
    return _data_service_instance


data_service = get_data_service()