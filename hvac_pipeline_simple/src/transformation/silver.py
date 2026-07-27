from sqlalchemy import text

from src.config import load_config
from src.database.connection import DatabaseConnection


class SilverTransformer:
    """
    Creates the cleaned and joined Silver HVAC table.
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


    def run(self):
        """
        Join Bronze features and targets
        and create the Silver table.
        """

        print("\nSILVER TRANSFORMATION STARTED")

        # Get table names from config
        features_table = self.tables["bronze_features"]
        targets_table = self.tables["bronze_targets"]
        silver_table = self.tables["silver"]

        # SQL transformation
        sql = text(
            f"""
            DROP TABLE IF EXISTS {silver_table};

            CREATE TABLE {silver_table} AS

            SELECT
                f.*,
                t.target

            FROM {features_table} AS f

            INNER JOIN {targets_table} AS t

                ON f.fault_type = t.fault_type

                AND f."Datetime" = t."Datetime";
            """
        )

        # Execute transformation inside PostgreSQL
        with self.engine.begin() as connection:
            connection.execute(sql)

        print(
            f"{silver_table} created successfully."
        )

        print(
            "\nSILVER TRANSFORMATION COMPLETED"
        )


    def close(self):
        """
        Close database resources.
        """

        self.database.close()


if __name__ == "__main__":

    # Create SilverTransformer object
    silver = SilverTransformer()

    # Run Silver transformation
    silver.run()

    # Close database resources
    silver.close()