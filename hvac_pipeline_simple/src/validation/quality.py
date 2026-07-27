from sqlalchemy import text

from src.config import load_config
from src.database.connection import DatabaseConnection


class DataQualityValidator:
    """
    Checks the quality of the Bronze HVAC tables.
    """

    def __init__(self):

        # Load configuration
        config = load_config()

        # Get table names
        self.tables = config["tables"]

        # Create database connection
        self.database = DatabaseConnection()

        # Get SQLAlchemy engine
        self.engine = self.database.get_engine()


    def get_count(self, table_name):
        """
        Count the number of rows in a table.
        """

        sql = text(
            f"SELECT COUNT(*) FROM {table_name}"
        )

        with self.engine.connect() as connection:
            result = connection.execute(sql)
            count = result.scalar()

        return count


    def get_missing_count(self, table_name, column_name):
        """
        Count missing values in one important column.
        """

        sql = text(
            f"""
            SELECT COUNT(*)
            FROM {table_name}
            WHERE {column_name} IS NULL
            """
        )

        with self.engine.connect() as connection:
            result = connection.execute(sql)
            count = result.scalar()

        return count


    def get_duplicate_count(self, table_name):
        """
        Count duplicate business keys.

        A record should be unique using:
        fault_type + Datetime
        """

        sql = text(
            f"""
            SELECT COUNT(*)
            FROM
            (
                SELECT fault_type, "Datetime"
                FROM {table_name}
                GROUP BY fault_type, "Datetime"
                HAVING COUNT(*) > 1
            ) duplicates
            """
        )

        with self.engine.connect() as connection:
            result = connection.execute(sql)
            count = result.scalar()

        return count


    def run(self):
        """
        Run all data quality checks.
        """

        print("\nDATA QUALITY VALIDATION STARTED")

        features_table = self.tables["bronze_features"]
        targets_table = self.tables["bronze_targets"]

        # -----------------------------------
        # 1. Row count check
        # -----------------------------------

        feature_rows = self.get_count(
            features_table
        )

        target_rows = self.get_count(
            targets_table
        )

        print("\n1. ROW COUNTS")

        print(
            "Feature rows:",
            feature_rows
        )

        print(
            "Target rows:",
            target_rows
        )

        # -----------------------------------
        # 2. Missing key check
        # -----------------------------------

        print("\n2. MISSING KEY VALUES")

        feature_missing = self.get_missing_count(
            features_table,
            '"Datetime"'
        )

        target_missing = self.get_missing_count(
            targets_table,
            '"Datetime"'
        )

        print(
            "Missing feature timestamps:",
            feature_missing
        )

        print(
            "Missing target timestamps:",
            target_missing
        )

        # -----------------------------------
        # 3. Duplicate check
        # -----------------------------------

        print("\n3. DUPLICATE BUSINESS KEYS")

        feature_duplicates = self.get_duplicate_count(
            features_table
        )

        target_duplicates = self.get_duplicate_count(
            targets_table
        )

        print(
            "Feature duplicates:",
            feature_duplicates
        )

        print(
            "Target duplicates:",
            target_duplicates
        )

        # -----------------------------------
        # Final result
        # -----------------------------------

        if feature_duplicates > 0:
            raise ValueError(
                "Validation failed: "
                "duplicate feature keys found."
            )

        if target_duplicates > 0:
            raise ValueError(
                "Validation failed: "
                "duplicate target keys found."
            )

        print(
            "\nDATA QUALITY VALIDATION COMPLETED SUCCESSFULLY"
        )


    def close(self):
        """
        Close database resources.
        """

        self.database.close()


if __name__ == "__main__":

    validator = DataQualityValidator()

    validator.run()

    validator.close()