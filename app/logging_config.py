import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/Yehezkiel/E-Nose-Backend/logs/app.log'),
        logging.StreamHandler()
    ]
)