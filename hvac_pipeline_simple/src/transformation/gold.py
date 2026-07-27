from sqlalchemy import text

from src.config import load_config
from src.database.connection import DatabaseConnection


class GoldTransformer:
    """
    Creates an analytics-ready hourly summary from Silver data.
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
        Aggregate minute-level Silver data into hourly metrics.
        """

        print("\nGOLD TRANSFORMATION STARTED")

        silver_table = self.tables["silver"]
        gold_table = self.tables["gold"]

        sql = text(
            f"""
            DROP TABLE IF EXISTS {gold_table};

            CREATE TABLE {gold_table} AS

            SELECT
                fault_type,
                target,

                DATE_TRUNC(
                    'hour',
                    "Datetime"::timestamp
                ) AS hour,

                AVG("ZONE_TEMP_1") AS zone_temp_1_avg,
                MIN("ZONE_TEMP_1") AS zone_temp_1_min,
                MAX("ZONE_TEMP_1") AS zone_temp_1_max,

                AVG("ZONE_TEMP_2") AS zone_temp_2_avg,
                MIN("ZONE_TEMP_2") AS zone_temp_2_min,
                MAX("ZONE_TEMP_2") AS zone_temp_2_max,

                AVG("ZONE_TEMP_3") AS zone_temp_3_avg,
                MIN("ZONE_TEMP_3") AS zone_temp_3_min,
                MAX("ZONE_TEMP_3") AS zone_temp_3_max,

                AVG("ZONE_TEMP_4") AS zone_temp_4_avg,
                MIN("ZONE_TEMP_4") AS zone_temp_4_min,
                MAX("ZONE_TEMP_4") AS zone_temp_4_max,

                AVG("ZONE_TEMP_5") AS zone_temp_5_avg,
                MIN("ZONE_TEMP_5") AS zone_temp_5_min,
                MAX("ZONE_TEMP_5") AS zone_temp_5_max

            FROM {silver_table}

            GROUP BY
                fault_type,
                target,
                DATE_TRUNC(
                    'hour',
                    "Datetime"::timestamp
                )

            ORDER BY
                fault_type,
                hour;
            """
        )

        # PostgreSQL performs the aggregation
        with self.engine.begin() as connection:
            connection.execute(sql)

        print(
            f"{gold_table} created successfully."
        )

        print(
            "\nGOLD TRANSFORMATION COMPLETED"
        )


    def close(self):
        """
        Close database resources.
        """

        self.database.close()


if __name__ == "__main__":

    gold = GoldTransformer()

    gold.run()

    gold.close()