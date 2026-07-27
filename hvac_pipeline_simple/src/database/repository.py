import pandas as pd

from src.config import load_config
from src.database.connection import DatabaseConnection


class HVACRepository:
    """
    Reads HVAC data from PostgreSQL.
    """

    def __init__(self):

        # Load project configuration
        self.config = load_config()

        # Get table names from config.yml
        self.tables = self.config["tables"]

        # Create database connection object
        self.database = DatabaseConnection()

        # Get the SQLAlchemy engine
        self.engine = self.database.get_engine()


    def get_features(self):
        """
        Read the raw HVAC features table.
        """

        table_name = self.tables["raw_features"]

        print(f"Reading table: {table_name}")

        data = pd.read_sql_table(
            table_name,
            self.engine
        )

        return data


    def get_targets(self):
        """
        Read the raw HVAC targets table.
        """

        table_name = self.tables["raw_targets"]

        print(f"Reading table: {table_name}")

        data = pd.read_sql_table(
            table_name,
            self.engine
        )

        return data


    def close(self):
        """
        Close the database connection.
        """

        self.database.close()


if __name__ == "__main__":

    # Create repository object
    repository = HVACRepository()

    # Read features
    features = repository.get_features()

    # Read targets
    targets = repository.get_targets()

    # Display basic information
    print("\nFEATURE DATA")
    print("Rows:", len(features))
    print("Columns:", len(features.columns))
    print(features.head())

    print("\nTARGET DATA")
    print("Rows:", len(targets))
    print("Columns:", len(targets.columns))
    print(targets.head())

    # Close database connection
    repository.close()