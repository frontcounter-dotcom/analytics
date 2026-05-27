# conda env info_audit_py3.13:
# email_validator==2.3.0
# numpy==2.4.4
# pandas==3.0.2
# phonenumbers==9.0.18
# typeguard==4.5.1

import logging
from typing import Final, List
from datetime import datetime

import email_validator
import numpy as np
import pandas as pd
import phonenumbers
from typeguard import typechecked


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

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
TODAY = str(datetime.today())


@typechecked
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


@typechecked
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


@typechecked
def find_and_delete_invalid(df: pd.DataFrame) -> pd.DataFrame:
    """Validate contact fields, and delete invalid contact info."""
    df = find_and_delete_invalid_emails(df=df)

    df = find_and_delete_invalid_phone_nos(df=df, phone_col=Columns.PHONE)
    df = find_and_delete_invalid_phone_nos(df=df, phone_col=Columns.SECONDARY_TEL)
    
    return df

@typechecked
def find_and_delete_invalid_emails(df: pd.DataFrame) -> pd.DataFrame:
    """Format and validate email, and delete invalid."""
    normalized_emails = []
    for email in df[Columns.EMAIL]:
        email_validated = np.nan
        try:
            email = "" if email == np.nan else email
            email_validated = (
                email_validator.validate_email(str(email), check_deliverability=False).normalized
                if email
                else np.nan
            )

        except email_validator.EmailNotValidError:
            float_email = np.nan
            try:
                float_email = float(email)
                if not np.isnan(float(email)):
                    logging.warning(f"Found invalid email {email}. Replacing with `np.nan`")
            except ValueError:
                logging.warning(f"Found invalid email {email}. Replacing with `np.nan`")

        normalized_emails.append(email_validated)
    
    df[Columns.EMAIL] = normalized_emails

    return df


# Borrowed and modified from https://github.com/crickets-and-comb/bfb_delivery
@typechecked
def find_and_delete_invalid_phone_nos(df: pd.DataFrame, phone_col: str) -> pd.DataFrame:
    """Format and validate phone numbers, and delete invalid."""
    df[phone_col] = df[phone_col].astype(str).str.strip()
    df[phone_col] = df[phone_col].apply(lambda x: '' if (x is np.nan or x is None) else x)
    df[phone_col] = df[phone_col].apply(lambda x: x[:-2] if x.endswith(".0") else x)

    formatting_df = df.copy()
    formatting_df["formatted_numbers"] = formatting_df[phone_col].apply(
        lambda number: "+1" + number if (len(number) > 0 and number[0] != "+") else number
    )
    
    parsed_nos = []
    for number in formatting_df['formatted_numbers']:
        parsed_no = number
        if len(number) > 0:
            try:
                parsed_no = phonenumbers.parse(number)
            except Exception as e:
                parsed_no = ""
                logger.warning(f"Unable to parse phone number: {number}")
        parsed_nos.append(parsed_no)

    formatting_df["formatted_numbers"] = parsed_nos

    formatting_df["is_valid"] = formatting_df["formatted_numbers"].apply(
        lambda number: (
            phonenumbers.is_valid_number(number)
            if isinstance(number, phonenumbers.phonenumber.PhoneNumber)
            else True
        )
    )
    if not formatting_df["is_valid"].all():
        invalid_numbers = formatting_df[~formatting_df["is_valid"]]
        logger.warning(
            f"Invalid phone numbers found in {phone_col}, deleting:\n{invalid_numbers[phone_col].to_list()}"
        )
        invalid_numbers_fp = f"{OUTPUT_DIR}/invalid_numbers_{phone_col}_{TODAY}.csv"
        logging.info(f"Saving invalid numbers for {phone_col} to {invalid_numbers_fp}")
        invalid_numbers.to_csv(invalid_numbers_fp)

    def _nan_invalids(row):
        return np.nan if not row["is_valid"] else row["formatted_numbers"]
    
    formatting_df["formatted_numbers"] = formatting_df.apply(_nan_invalids, axis=1)

    formatting_df["formatted_numbers"] = [
        (
            str(
                phonenumbers.format_number(
                    number, num_format=phonenumbers.PhoneNumberFormat.INTERNATIONAL
                )
            )
            if isinstance(number, phonenumbers.phonenumber.PhoneNumber)
            else number
        )
        for number in formatting_df["formatted_numbers"].to_list()
    ]

    df[phone_col] = formatting_df["formatted_numbers"]

    return df


@typechecked
def save_output(to_email_df: pd.DataFrame, to_call_df: pd.DataFrame) -> None:
    """Save outputs."""
    to_email_fp = f"{OUTPUT_DIR}/to_email_{TODAY}.csv"
    to_call_fp = f"{OUTPUT_DIR}/to_call_{TODAY}.csv"

    logging.info(f"Saving to_email_df to {to_email_fp}")
    to_email_df.to_csv(to_email_fp)

    logging.info(f"Saving to_call_df to {to_call_fp}")
    to_call_df.to_csv(to_call_fp)

    return


if __name__ == "__main__":
    main()