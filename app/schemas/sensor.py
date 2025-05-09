# from pydantic import BaseModel, ConfigDict
# from datetime import datetime
# from typing import Optional


# class SensorBase(BaseModel):
#     timestamp: datetime
#     mq135: float
#     mq2: float
#     mq4: float
#     mq7: float
#     kualitas: Optional[str] = None
# class SensorCreate(SensorBase):
#     """Skema untuk menerima data dari sensor_reader.py"""
#     pass

# class SensorResponse(SensorBase):
#     """Skema untuk mengembalikan data sensor dari database"""
#     id: int

#     model_config = ConfigDict(from_attributes=True)

from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class SensorCreate(BaseModel):
    timestamp: Optional[str] = None
    mq135: Optional[float] = None
    mq2: Optional[float] = None
    mq4: Optional[float] = None
    mq7: Optional[float] = None
    kualitas: Optional[str] = None

class SensorResponse(BaseModel):
    id: int
    timestamp: datetime
    mq135: Optional[float]
    mq2: Optional[float]
    mq4: Optional[float]
    mq7: Optional[float]
    kualitas: Optional[str]

    class Config:
        from_attributes = True  # Untuk Pydantic v2, gantikan orm_mode
