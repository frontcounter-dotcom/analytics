# conda env info_audit_py3.13:
# numpy==2.4.4
# pandas==3.0.2

from typing import Final, List
from datetime import datetime
import logging

import numpy as np
import pandas as pd

class Columns:
    ADDRESS = "Address"
    EMAIL = "Email"
    EMAIL_OPT_IN = "Email Opt In"
    LAST_ORDER = "Last Order"
    NAME = "Name"
    PHONE = "Phone"
    SECONDARY_TEL = "Secondary Tel"
    TOTAL_ORDERS = "Total orders"

CUSTIE_CSV_FP: Final[str] = "~/Downloads/CC-Customers_2019-11-26-2026-05-21.csv"
CONTACT_COLS: Final[List[str]] = [Columns.EMAIL, Columns.PHONE, Columns.ADDRESS]
CONTACT_COLS_ALL: Final[List[str]] = CONTACT_COLS + [Columns.SECONDARY_TEL]
OUTPUT_DIR: Final[str] = "~/analytics/customer_info"

def main() -> None:
    custie_df = pd.read_csv(CUSTIE_CSV_FP)
    custie_df = clean(df=custie_df)
    custie_df = find_and_delete_invalid(df=custie_df)
    custie_df = custie_df[
        ~(custie_df[CONTACT_COLS_ALL].isna().all(axis=1) &
        (custie_df[Columns.TOTAL_ORDERS] > 0))
    ]

    missing_contact_df = custie_df[custie_df[CONTACT_COLS].isna().any(axis=1)]
    to_email_df = missing_contact_df[
        missing_contact_df[Columns.EMAIL].notna() &
        (missing_contact_df[Columns.EMAIL_OPT_IN] == True)
    ]
    to_call_df = missing_contact_df[
        (
            missing_contact_df[Columns.EMAIL].isna() |
            missing_contact_df[Columns.EMAIL_OPT_IN] != True
        ) &
        (
            missing_contact_df[Columns.PHONE].notna() |
            missing_contact_df[Columns.SECONDARY_TEL].notna()
        )
    ].sort_values(by=Columns.LAST_ORDER, ascending=False)

    save_output(to_email_df=to_email_df, to_call_df=to_call_df)

    return



def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Clean up dataframe and set types."""
    df[Columns.EMAIL_OPT_IN] = [val if val == 1 else 0 for val in df['Email Opt In']]

    df = df.astype(
        dtype={
            Columns.ADDRESS: str,
            Columns.EMAIL: str,
            Columns.EMAIL_OPT_IN: bool,
            Columns.LAST_ORDER: 'datetime64[ns]',
            Columns.NAME: str,
            Columns.PHONE: str,
            Columns.SECONDARY_TEL: str,
            Columns.TOTAL_ORDERS: int
        }
    )

    df = df.replace('', np.nan)
    df = df.replace(r'^\s*$', np.nan, regex=True)

    df[Columns.TOTAL_ORDERS] = df[Columns.TOTAL_ORDERS].fillna(0)

    return df


def find_and_delete_invalid(df: pd.DataFrame) -> pd.DataFrame:
    """Validate contact fields, and delete invalid contact info."""
    ...
    return df


def save_output(to_email_df: pd.DataFrame, to_call_df: pd.DataFrame) -> None:
    """Save outputs."""
    today = str(datetime.today())
    to_email_fp = f"{OUTPUT_DIR}/to_email_{today}.csv"
    to_call_fp = f"{OUTPUT_DIR}/to_call_{today}.csv"

    logging.info(f"Saving to_email_df to {to_email_fp}")
    to_email_df.to_csv(to_email_fp)

    logging.info(f"Saving to_call_df to {to_call_fp}")
    to_call_df.to_csv(to_call_fp)

    return


if __name__ == "__main__":
    main()