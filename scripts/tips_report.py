# Calculates the expected tips per employee, produces report.
# conda env tips_report_py3.13, 2026-05-14:
# click 8.2.1
# pandas 3.0.2
# python 3.14.4
# formatting/linting:
# black==26.3.1
# flake8==7.3.0
# isort==8.0.1

import logging
from datetime import datetime
from typing import Final

import click
import pandas as pd
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATE_FORMAT: Final[str] = "%Y-%m-%d"


class ColumnsPayrollIn:
    EMPLOYEE = "Employee"
    END_DATE = "end date"
    START_DATE = "start date"
    TOTAL = "total"


class ColumnsHours:
    DAILY_HOURS = "daily_hours"
    END_DATE = "end date"
    START_DATE = "start date"
    NAME = "name"
    SHIFT_HOURS = "shift_hours"
    TOTAL = "total"


class ColumnsRevenueIn:
    PAID_DATE = "Paid Date"
    TIP = "Tip"


class ColumnsTips:
    DATE = "date"
    TIP = "tip"


class ColumnsSummary:
    EMPLOYEE_HOURS = "employee_hours"
    EMPLOYEE_TIPS = "employee_tips"
    EMPLOYEE = "employee"
    TOTAL_HOURS = "total_hours"
    TOTAL_TIPS = "total_tips"


@click.command()
@click.option(
    "--payroll_fp",
    type=str,
    required=True,
    help="From Humanity, not including paid leave.",
    # "~/analytics/tips_reports/2026.01.02_2026.05.27/Report - timesheets - 05_28_2026 - 12_48pm"
)
@click.option(
    "--revenue_fp",
    type=str,
    required=True,
    help="From CleanCloud, orders(revenue).",
    # "~/analytics/tips_reports/2026.01.02_2026.05.27/CC-Revenue-01012026-31122026.csv"
)
@click.option(
    "--output_dir",
    type=str,
    required=True,
    help="Where to write summary dataframes.",
    # "~/analytics/tips_reports/2026.01.02_2026.05.27"
)
@click.option(
    "--start_date",
    type=str,
    required=True,
    help=f"First day of period. Inclusive range. {DATE_FORMAT}",
)
@click.option(
    "--end_date",
    type=str,
    required=True,
    help=f"Last day of period. Inclusive range. {DATE_FORMAT}",
)
def main(payroll_fp: str, revenue_fp: str, output_dir: str, start_date: str, end_date: str) -> None:
    """Calculates the expected tips per employee, produces report."""
    start_date_fmt = datetime.strptime(start_date, DATE_FORMAT)
    end_date_fmt = datetime.strptime(end_date, DATE_FORMAT)

    hours_df = _get_hours_df(
        payroll_fp=payroll_fp, start_date=start_date_fmt, end_date=end_date_fmt
    )
    tips_df = _get_tips_df(
        revenue_fp=revenue_fp, start_date=start_date_fmt, end_date=end_date_fmt
    )

    summary_df = _get_summary_df(hours_df=hours_df, tips_df=tips_df)

    daily_tips_df = tips_df.groupby(by=ColumnsTips.DATE).sum()

    time_stamp = str(datetime.today())
    summary_df_fp = Path(output_dir, f"summary_{time_stamp}.csv")
    logger.info(f"Writing summary_df to {summary_df_fp}")
    summary_df.to_csv(summary_df_fp)

    daily_tips_df_fp = Path(output_dir, f"daily_tips_{time_stamp}.csv")
    logger.info(f"Writing daily_tips_df to {daily_tips_df_fp}")
    daily_tips_df.to_csv(daily_tips_df_fp)


def _get_hours_df(
    payroll_fp: str, start_date: datetime, end_date: datetime
) -> pd.DataFrame:
    hours_df = pd.read_csv(payroll_fp)

    rename_dict = {
        ColumnsPayrollIn.EMPLOYEE: ColumnsHours.NAME,
        ColumnsPayrollIn.END_DATE: ColumnsHours.END_DATE,
        ColumnsPayrollIn.START_DATE: ColumnsHours.START_DATE,
        ColumnsPayrollIn.TOTAL: ColumnsHours.TOTAL,
    }
    hours_df.rename(columns=rename_dict, inplace=True)
    hours_df = hours_df[list(rename_dict.values())]

    hours_df = hours_df[~hours_df[ColumnsHours.NAME].isna()]

    hours_df = hours_df.astype(
        {
            ColumnsHours.NAME: str,
            ColumnsHours.TOTAL: float,
        }
    )

    _validate_payroll_dates(hours_df=hours_df, start_date=start_date, end_date=end_date)

    hours_df = hours_df[[ColumnsHours.NAME, ColumnsHours.TOTAL]]

    return hours_df


def _get_tips_df(
    revenue_fp: str, start_date: datetime, end_date: datetime
) -> pd.DataFrame:
    tips_df = pd.read_csv(revenue_fp)

    rename_dict = {
        ColumnsRevenueIn.PAID_DATE: ColumnsTips.DATE,
        ColumnsRevenueIn.TIP: ColumnsTips.TIP,
    }
    tips_df.rename(columns=rename_dict, inplace=True)
    tips_df = tips_df[list(rename_dict.values())]

    tips_df = tips_df.astype({ColumnsTips.DATE: str, ColumnsTips.TIP: float})
    tips_df[ColumnsTips.DATE] = pd.to_datetime(pd.to_datetime(tips_df[ColumnsTips.DATE]).dt.date)
    tips_df = tips_df[
        (tips_df[ColumnsTips.DATE] >= start_date)
        & (tips_df[ColumnsTips.DATE] <= end_date)
    ]
    if len(tips_df) < 1:
        raise ValueError(f"Expected revenue records within {start_date} and {end_date}")

    def _validate_date(date: datetime, start_or_end: str) -> None:
        max_date = tips_df[ColumnsTips.DATE].max()
        min_date = tips_df[ColumnsTips.DATE].min()
        if date not in set(tips_df[ColumnsTips.DATE]):
            raise ValueError(
                f"In revenue dataframe, expected {start_or_end} date {date} to be within {min_date} and {max_date}"
            )

        return

    _validate_date(date=start_date, start_or_end="start")
    _validate_date(date=end_date, start_or_end="end")

    return tips_df


def _get_summary_df(hours_df: pd.DataFrame, tips_df: pd.DataFrame) -> pd.DataFrame:
    summary_df = hours_df.copy()
    summary_df.rename(
        columns={ColumnsHours.TOTAL: ColumnsSummary.EMPLOYEE_HOURS, ColumnsHours.NAME: ColumnsSummary.EMPLOYEE}, inplace=True
    )
    summary_df[ColumnsSummary.TOTAL_TIPS] = tips_df[ColumnsTips.TIP].sum()
    summary_df[ColumnsSummary.TOTAL_HOURS] = summary_df[
        ColumnsSummary.EMPLOYEE_HOURS
    ].sum()
    summary_df[ColumnsSummary.EMPLOYEE_TIPS] = (
        summary_df[ColumnsSummary.EMPLOYEE_HOURS]
        / summary_df[ColumnsSummary.TOTAL_HOURS]
    ) * summary_df[ColumnsSummary.TOTAL_TIPS]
    
    summary_df = summary_df[
        [
            ColumnsSummary.EMPLOYEE,
            ColumnsSummary.EMPLOYEE_HOURS,
            ColumnsSummary.TOTAL_HOURS,
            ColumnsSummary.TOTAL_TIPS,
            ColumnsSummary.EMPLOYEE_TIPS,
        ]
    ]

    return summary_df


def _validate_payroll_dates(
    hours_df: pd.DataFrame, start_date: datetime, end_date: datetime
) -> None:
    hours_df[ColumnsHours.START_DATE] = pd.to_datetime(hours_df[ColumnsHours.START_DATE])
    hours_df[ColumnsHours.END_DATE] = pd.to_datetime(hours_df[ColumnsHours.END_DATE])

    def _validate_date(
        sr: pd.Series, expected_date: datetime, start_or_end: str
    ) -> None:
        dates = list(sr.unique())
        if len(dates) != 1:
            raise ValueError(
                f"In payroll dataframe, expected single {start_or_end} date, but got {dates}."
            )
        elif dates[0] != expected_date:
            raise ValueError(
                f"In payroll dataframe, expected {start_or_end} to equal {expected_date}, but got {dates[0]}"
            )
        else:
            pass

        return

    _validate_date(
        sr=hours_df[ColumnsHours.START_DATE],
        expected_date=start_date,
        start_or_end="start",
    )
    _validate_date(
        sr=hours_df[ColumnsHours.END_DATE], expected_date=end_date, start_or_end="end"
    )


if __name__ == "__main__":
    main()
