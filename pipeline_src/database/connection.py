from sqlalchemy import create_engine
from pipeline_src.config import load_config


class DatabaseConnection:
    """
    Creates and manages the PostgreSQL database connection.
    """

    def __init__(self):
        # Load settings from config.yml
        config = load_config()

        # Get only the database section
        db = config["database"]

        # Create the PostgreSQL connection URL
        database_url = (
            f"postgresql+psycopg2://"
            f"{db['user']}:{db['password']}"
            f"@{db['host']}:{db['port']}/{db['database']}"
        )

        # Create the database engine
        self.engine = create_engine(database_url)

    def get_engine(self):
        """
        Give the database connection to other classes.
        """
        return self.engine

    def close(self):
        """
        Close database connections.
        """
        self.engine.dispose()


if __name__ == "__main__":
    from sqlalchemy import text

    # Create our DatabaseConnection object
    database = DatabaseConnection()

    # Get the SQLAlchemy engine
    engine = database.get_engine()

    # Open a real connection to PostgreSQL
    with engine.connect() as connection:

        # Simple test query
        result = connection.execute(
            text("SELECT 1")
        )

        print("PostgreSQL connected successfully!")
        print("Test result:", result.scalar())

    # Close the engine
    database.close()

    print("Database connection closed.")  