import pandas as pd

def read_csv(file_path):
    """
    Reads a CSV file, filters for Caldas department, and returns a cleaned DataFrame.

    Parameters:
    file_path (str): The path to the CSV file.

    Returns:
    pd.DataFrame: A DataFrame containing only string values for all data.
    """

    try:
        df = pd.read_csv(file_path, dtype=str, low_memory=False)
        df = df.apply(lambda col: col.str.strip('"'))

        print(f"Datos cargados: {df.shape[0]} filas, {df.shape[1]} columnas")
        return df
    except Exception as e:
        print(f"An error occurred while reading the CSV file: {e}")
        return None


def cast_columns(df):
    """
    Casts columns to their appropriate data types.

    Parameters:
    df (pd.DataFrame): The raw DataFrame with all string values.

    Returns:
    pd.DataFrame: A DataFrame with appropriate data types.
    """

    numeric_cols = [
        'punt_matematicas', 'punt_lectura_critica', 'punt_global',
        'punt_c_naturales', 'punt_sociales_ciudadanas', 'punt_ingles'
    ]

    integer_cols = ['periodo']

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    for col in integer_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')

    print(f"Tipos de datos actualizados.")
    print(df.dtypes)
    return df


def save_csv(df, output_path='caldas_saber11.csv'):
    """
    Saves a DataFrame to a CSV file.

    Parameters:
    df (pd.DataFrame): The DataFrame to save.
    output_path (str): The path to the output CSV file. Defaults to 'caldas_saber11.csv'.
    """
    
    try:
        df.to_csv(output_path, index=False)
        print(f"Archivo guardado en: {output_path}")
    except Exception as e:
        print(f"An error occurred while saving the CSV file: {e}")


csv_data = read_csv('caldas_saber11_raw.csv')

if csv_data is not None:
    csv_data = cast_columns(csv_data)
    save_csv(csv_data)