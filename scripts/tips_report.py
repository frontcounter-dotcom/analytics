# Calculates the expected tips per employee, produces report.
# conda env tips_report_py3.13, 2026-05-14:
# click 8.2.1
# pandas 3.0.2
# python 3.14.4

from datetime import datetime
from typing import Final

import click
import pandas as pd

DATE_FORMAT: Final[str] = "%Y-%m-%d"

@click.command()
@click.option("--payroll_fp", type=str, required=True)
@click.option("--revenue_fp", type=str, required=True)
@click.option("--start_date", type=str, required=True, help=f"First day of period. Inclusive range. {DATE_FORMAT}")
@click.option("--end_date", type=str, required=True, help=f"Last day of period. Inclusive range. {DATE_FORMAT}")
def main(payroll_fp: str, revenue_fp: str, start_date: str, end_date: str) -> None:
    """Calculates the expected tips per employee, produces report."""
    start_date_fmt = datetime.strptime(start_date, DATE_FORMAT)
    end_date_fmt = datetime.strptime(end_date, DATE_FORMAT)

    hours_df = pd.read_csv(payroll_fp)
    tips_df = pd.read_csv(revenue_fp)

    hours_df.rename(columns={"Employee Name": "name"}, inplace=True)
    employees = list(set(hours_df["name"]))

    hours_df = hours_df.astype({"Year": int, "Month": int, "Day": int})
    hours_df['date'] = pd.to_datetime(hours_df[["Year", "Month", "Day"]])
    hours_df = hours_df[(hours_df["date"] >= start_date_fmt) & (hours_df["date"] <= end_date_fmt)]
    
    hours_df = hours_df.astype({"Regular": float, "Special": float, "Overtime": float, "name": str})
    hours_df['shift_hours'] = hours_df[["Regular", "Special", "Overtime"]].sum(axis=1)
    hours_df = hours_df[["date", "name", "shift_hours"]]
    hours_df = hours_df.groupby(["date", "name"], as_index=False)['shift_hours'].sum()

    hours_df = hours_df.pivot(index="date", columns="name", values="shift_hours").reset_index().fillna(0)

    hours_df["daily_hours"] = hours_df[employees].sum(axis=1)

    tips_df.rename(columns={"Tips": "daily_tips", "Date": "date"}, inplace=True)
    tips_df = tips_df[["date", "daily_tips"]]

    tips_df = tips_df.astype({"date": str})
    tips_df["date"] = pd.to_datetime(tips_df["date"])
    tips_df = tips_df[(tips_df["date"] >= start_date_fmt) & (tips_df["date"] <= end_date_fmt)]

    tips_df = tips_df.astype({"daily_tips": float})

    tips_df = pd.merge(left=hours_df, right=tips_df, on="date", how="outer").fillna(0)

    tips_df = tips_df[tips_df["daily_hours"] > 0]
    tips_df["hourly_tips"] = tips_df["daily_tips"] / tips_df["daily_hours"]

    breakpoint()
    daily_tip_summary_df = tips_df.melt(id_vars=["date", "daily_hours", "daily_tips", "hourly_tips"], value_vars=employees, var_name="name", value_name="hours").reset_index()
    daily_tip_summary_df["employee_tips"] = daily_tip_summary_df["hourly_tips"] * daily_tip_summary_df["hours"]

    summary_tip_hours_df = daily_tip_summary_df[["date", "daily_hours", "daily_tips"]].groupby("date").sum()

    hourly_tip_summary_df = daily_tip_summary_df[["date", "daily_hours", "daily_tips"]].drop_duplicates()


if __name__ == "__main__":
    main()