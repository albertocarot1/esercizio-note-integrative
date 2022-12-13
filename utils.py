import math
from typing import List

import pandas as pd

# 2017 and 2018 can be column names as they infer the year
NUMBERS_ACCEPTED_COLUMN_NAME = (2017, 2018)


def has_float_cells(row: pd.Series):
    for cell in row:
        try:
            if isinstance(cell, str):
                cell = cell.replace('(', '-').replace(')', '').replace('.', '')
            if math.isnan(float(cell)):
                continue
            if cell in NUMBERS_ACCEPTED_COLUMN_NAME:
                continue
            return True
        except ValueError:
            continue
    return False


def clean_table(table: pd.DataFrame) -> pd.DataFrame:
    """
    Clean table, returning a DataFrame with two columns: the expense item, and the desired value (anno corrente/2018).
    Also, when present, the totali row at the end is present
    :param table:
    :return: the clean table. If there was an error somewhere, return an empty dataframe.
    """

    # Immediately return empty dataframe
    if all(table.isnull().values.all(axis=0)):
        return pd.DataFrame()

    cleaned_table: pd.DataFrame

    # Remove empty columns and rows
    cleaned_table = table.dropna(axis=1, how='all')
    cleaned_table = cleaned_table.dropna(how='all')

    # Some tables have - o nan instead of 0 for items with no expense
    cleaned_table = cleaned_table.replace('-', '0')
    cleaned_table = cleaned_table.replace('\.0$', '', regex=True)
    cleaned_table = cleaned_table.fillna('0')

    # Remove uninformative rows
    cleaned_table = cleaned_table[cleaned_table.iloc[:, 0].astype(str).str.contains("^_+$") == False]

    # If at least one element can be parsed to float, the row contains expenses,
    # and so the column headers used are from the previous row
    # (or the html parsed ones in case the first row contains a float)
    # The top rows before the actual expense items are deleted from the dataframe.
    for i, (row_id, row) in enumerate(cleaned_table.iterrows()):
        if has_float_cells(row):
            break
        else:
            columns = row.values
    if i > 0:
        cleaned_table.drop(cleaned_table.index[0:row_id], inplace=True)
        cleaned_table.columns = columns

    # Replace values between brackets with negatives
    cleaned_table = cleaned_table.astype(str)
    cleaned_table.iloc[:, 1:] = cleaned_table.iloc[:, 1:].replace('\(', '-', regex=True)
    cleaned_table.iloc[:, 1:] = cleaned_table.iloc[:, 1:].replace('\)', '', regex=True)
    cleaned_table.iloc[:, 1:] = cleaned_table.iloc[:, 1:].replace('\.', '', regex=True)

    # check that all elements in the first column can only be parsed to string (Expect list of expense items)
    try:
        cleaned_table.iloc[:, 0].astype('float')
        print("The first column that should contain only items names, but it contains numbers")
        return pd.DataFrame()
    except ValueError:
        try:

            cleaned_table.iloc[:, 1:].astype('float')
        except ValueError:
            print("All elements that should be numbers cannot be converted to float")
            return pd.DataFrame()

    return cleaned_table


def extract_expense_items(expenses_tables: List[pd.DataFrame], company: pd.Series):
    """
    Expect tables to have all numbers apart from the first column which is string.
    :param expenses_tables: list of Dataframe representing tables of a single company
    :param company: other data about the company
    :return: a dataframe with all expense items, and
    """
    desired_column_regex = "corrent|2018|corso|Corrent|Corso"
    expense_items, amounts, expense_types = [], [], []
    for table in expenses_tables:
        if table.empty:
            continue

        # "Totale/Totali" is not an expense item
        # if "Totale/Totali" matches the company's costi_servizi, add costi_servizi to the
        total_condition = table.iloc[:, 0].astype(str).str.contains(r"totale|totali|tot\.$|tot$|^0$", case=False)
        total_row = table[total_condition]
        if total_row.empty:
            # no total found, put unlikely number to make statement below fail
            total_value = -999999
        else:
            total_value = float(total_row.filter(regex=(desired_column_regex)).iloc[0, 0])

        table_wo_total = table[total_condition == False]
        # take the value in the column with "corrente/2018" in the column title
        table_amounts: List = table_wo_total.filter(regex=(desired_column_regex)).iloc[:, 0].astype(float).tolist()
        amounts.extend(table_amounts)

        if math.isclose(total_value, company['costi_produzione']):
            expense_types.extend(['costi_produzione'] * len(table_amounts))
        elif math.isclose(total_value, company['costi_servizi']):
            expense_types.extend(['costi_servizi'] * len(table_amounts))
        else:
            expense_types.extend(['altri_costi'] * len(table_amounts))
        table_items: List = table_wo_total.iloc[:, 0].astype(str).tolist()
        expense_items.extend(table_items)

    return pd.DataFrame(list(zip(expense_items, amounts, expense_types)),
                        columns=['Expense Item', 'Amount', 'Expense Type'])


def match_items_different_companies(companies: pd.DataFrame, expense_items: List[pd.DataFrame]):
    """
    Match based on simple regex voices for each different company's expenses.
    :param companies:
    :param expense_items:
    :return: a Dataframe including relevant fields of companies, and
    """
    company_expenses = pd.DataFrame()
    return company_expenses


if __name__ == '__main__':
    input_df = pd.read_csv('analisi_spesa_da_note_integrative_20210319.zip')
    tables_df = input_df['HTML'].apply(pd.read_html, decimal=",", thousands='.')

    expenses_items = []

    for (company_id, company), tables in zip(input_df.iterrows(), tables_df):
        if company_id == 25:
            print()

        cleaned_tables = [clean_table(t) for t in tables]
        expenses_items.append(extract_expense_items(cleaned_tables, company))

    match_items_different_companies(input_df, expenses_items)
