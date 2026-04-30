from dotenv import load_dotenv

load_dotenv()

from app.workers.sentiment_worker import main


if __name__ == "__main__":
    main()
