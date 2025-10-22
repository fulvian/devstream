import aiohttp
import fastapi
import pytest
import sqlalchemy
import numpy as np
import pandas as pd
from typing import Optional

app = fastapi.FastAPI()

@app.get('/')
async def root():
    return {'message': 'Hello World'}

# Test using multiple libraries to increase chances of hitting the 10% rollout
async def test_aiohttp_client():
    connector = aiohttp.TCPConnector(limit=30, limit_per_host=10)
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.get('https://httpbin.org/get') as response:
            return await response.json()

def test_pytest_fixture():
    @pytest.fixture
    def sample_data():
        return {"key": "value"}
    return sample_data

def test_sqlalchemy_usage():
    from sqlalchemy import create_engine, Column, Integer, String
    from sqlalchemy.ext.declarative import declarative_base

    Base = declarative_base()

    class User(Base):
        __tablename__ = 'users'
        id = Column(Integer, primary_key=True)
        name = Column(String)

    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    return engine

def test_numpy_operations():
    arr = np.array([1, 2, 3, 4, 5])
    return np.mean(arr)

def test_pandas_operations():
    df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
    return df.describe()