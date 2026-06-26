"""
研究AnyIO使用
"""
import os
from typing import TYPE_CHECKING
import asyncio
import anyio
from anyio import sleep, create_task_group, run, TaskHandle, CapacityLimiter