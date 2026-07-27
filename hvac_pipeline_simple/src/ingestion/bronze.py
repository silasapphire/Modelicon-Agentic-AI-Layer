from sqlalchemy import text

from src.config import load_config
from src.database.connection import DatabaseConnection


class BronzeIngestion:
    """
    Copies raw PostgreSQL tables into Bronze tables.
    """

    def __init__(self):

        # Load configuration
        config = load_config()

        # Get table names
        self.tables = config["tables"]

        # Create database connection
        self.database = DatabaseConnection()

        # Get database engine
        self.engine = self.database.get_engine()


    def copy_table(self, source_table, target_table):
        """
        Copy one PostgreSQL table into another table.
        """

        print(
            f"Copying {source_table} -> {target_table}"
        )

        # SQL command to recreate the Bronze table
        sql = text(
            f"""
            DROP TABLE IF EXISTS {target_table};

            CREATE TABLE {target_table} AS
            SELECT *
            FROM {source_table};
            """
        )

        # Begin a database transaction
        with self.engine.begin() as connection:

            # Execute the SQL
            connection.execute(sql)

        print(
            f"{target_table} created successfully."
        )


    def run(self):
        """
        Create all Bronze tables.
        """

        print("\nBRONZE INGESTION STARTED")

        self.copy_table(
            self.tables["raw_features"],
            self.tables["bronze_features"]
        )

        self.copy_table(
            self.tables["raw_targets"],
            self.tables["bronze_targets"]
        )

        print("\nBRONZE INGESTION COMPLETED")


    def close(self):
        """
        Close database connections.
        """

        self.database.close()


if __name__ == "__main__":

    bronze = BronzeIngestion()

    bronze.run()

    bronze.close()