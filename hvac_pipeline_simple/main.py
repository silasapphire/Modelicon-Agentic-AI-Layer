from src.ingestion.bronze import BronzeIngestion
from src.validation.quality import DataQualityValidator
from src.transformation.silver import SilverTransformer
from src.transformation.gold import GoldTransformer


def main():

    print("\n========== HVAC DATA PIPELINE STARTED ==========")

    # Step 1: Raw data -> Bronze
    bronze = BronzeIngestion()
    bronze.run()
    bronze.close()

    # Step 2: Validate Bronze data
    validator = DataQualityValidator()
    validator.run()
    validator.close()

    # Step 3: Bronze data -> Silver
    silver = SilverTransformer()
    silver.run()
    silver.close()

    # Step 4: Silver data -> Gold
    gold = GoldTransformer()
    gold.run()
    gold.close()

    print("\n========== HVAC DATA PIPELINE COMPLETED ==========")


if __name__ == "__main__":
    main()