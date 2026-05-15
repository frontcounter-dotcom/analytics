# Calculates the expected tips per employee, produces report.
# Running in conda env tips_report_py3.13
import pandas as pd
import click

@click.command()
@click.option("--payroll_fp", type=str, required=True)
@click.option("--revenue_fp", type=str, required=True)
def main(payroll_fp: str, revenue_fp: str) -> None:
    """Calculates the expected tips per employee, produces report."""
    # Get payroll and revenue CSVs.

    # Subspace and subselect.

    # Convert payroll to pivot table.

    # Join to revenue table by date.

    # Calculate expected tips per employee period. (Involves aggregating to pay period.)