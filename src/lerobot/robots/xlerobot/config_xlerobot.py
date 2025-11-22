# Copyright 2024 The HuggingFace Inc. team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from dataclasses import dataclass, field
from typing import Tuple
import glob
import os
import subprocess
from serial.tools import list_ports
from lerobot.cameras.configs import CameraConfig, Cv2Rotation, ColorMode
from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig
from lerobot.cameras.realsense import RealSenseCamera, RealSenseCameraConfig

from ..config import RobotConfig

port1 = None
port2 = None

def _get_xlerobot_port(serial1: str, serial2: str) -> Tuple[str, str]:
    global port1, port2
    if port1 and port2:
        return port1, port2
        
    for pattern in ["/dev/ttyACM*", "/COM*"]:
        # 展开通配符
        devices = glob.glob(pattern)
        for device in devices:
            info = _get_device_info(device)
            if info['serial'] == serial1:
                port1 = device
            if info['serial'] == serial2:
                port2 = device
    print("debug: port1:", port1, "port2:", port2, flush=True)
    return port1, port2


def _get_device_info(device_path: str) -> dict:
    """
    获取设备详细信息
    
    Args:
        device_path: 设备路径，如 /dev/ttyUSB0
        
    Returns:
        设备信息字典
    """
    info = {
        'path': device_path,
        'exists': os.path.exists(device_path),
        'vendor_id': None,
        'product_id': None,
        'serial': None,
        'description': None,
        'manufacturer': None,
        'product': None,
    }
    
    # 尝试使用 udevadm 获取详细信息
    try:
        result = subprocess.run(
            ['udevadm', 'info', '-q', 'property', '-n', device_path],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    if key == 'ID_VENDOR_ID':
                        info['vendor_id'] = value
                    elif key == 'ID_MODEL_ID':
                        info['product_id'] = value
                    elif key == 'ID_SERIAL_SHORT':
                        info['serial'] = value
                    elif key == 'ID_VENDOR':
                        info['manufacturer'] = value
                    elif key == 'ID_MODEL':
                        info['product'] = value
                    elif key == 'ID_USB_INTERFACE_NUM':
                        pass  # 忽略接口编号
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        pass
    
    # 尝试使用 pyserial 获取信息
    try:
        ports = list_ports.comports()
        for port in ports:
            if port.device == device_path:
                info['description'] = port.description
                if not info['manufacturer']:
                    info['manufacturer'] = port.manufacturer
                if not info['product']:
                    info['product'] = port.product
                if not info['serial']:
                    info['serial'] = port.serial_number
                if not info['vendor_id']:
                    info['vendor_id'] = f"{port.vid:04x}" if port.vid else None
                if not info['product_id']:
                    info['product_id'] = f"{port.pid:04x}" if port.pid else None
                break
    except Exception:
        pass
    
    return info

def xlerobot_cameras_config() -> dict[str, CameraConfig]:
    return {
        # "left_wrist": OpenCVCameraConfig(
        #     index_or_path="/dev/video0", fps=30, width=640, height=480, rotation=Cv2Rotation.NO_ROTATION
        # ),

        # "right_wrist": OpenCVCameraConfig(
        #     index_or_path="/dev/video2", fps=30, width=640, height=480, rotation=Cv2Rotation.NO_ROTATION
        # ),  

        # "head(RGDB)": OpenCVCameraConfig(
        #     index_or_path="/dev/video2", fps=30, width=640, height=480, rotation=Cv2Rotation.NO_ROTATION
        # ),                     
        
        # "head": RealSenseCameraConfig(
        #     serial_number_or_name="125322060037",  # Replace with camera SN
        #     fps=30,
        #     width=1280,
        #     height=720,
        #     color_mode=ColorMode.BGR, # Request BGR output
        #     rotation=Cv2Rotation.NO_ROTATION,
        #     use_depth=True
        # ),
    }


@RobotConfig.register_subclass("xlerobot")
@dataclass
class XLerobotConfig(RobotConfig):
    
    serial1: str = "5A7C116455"  # serial number of the bus (so101 + head camera)
    serial2: str = "5A7C118369"  # serial number of the bus (same as lekiwi setup)
    port1, port2 = _get_xlerobot_port(serial1, serial2)
    disable_torque_on_disconnect: bool = True

    # `max_relative_target` limits the magnitude of the relative positional target vector for safety purposes.
    # Set this to a positive scalar to have the same value for all motors, or a list that is the same length as
    # the number of motors in your follower arms.
    max_relative_target: int | None = None

    cameras: dict[str, CameraConfig] = field(default_factory=xlerobot_cameras_config)

    # Set to `True` for backward compatibility with previous policies/dataset
    use_degrees: bool = False

    teleop_keys: dict[str, str] = field(
        default_factory=lambda: {
            # Movement
            "forward": "i",
            "backward": "k",
            "left": "j",
            "right": "l",
            "rotate_left": "u",
            "rotate_right": "o",
            # Speed control
            "speed_up": "n",
            "speed_down": "m",
            # quit teleop
            "quit": "b",
        }
    )



@dataclass
class XLerobotHostConfig:
    # Network Configuration
    port_zmq_cmd: int = 5555
    port_zmq_observations: int = 5556

    # Duration of the application
    connection_time_s: int = 3600

    # Watchdog: stop the robot if no command is received for over 0.5 seconds.
    watchdog_timeout_ms: int = 500

    # If robot jitters decrease the frequency and monitor cpu load with `top` in cmd
    max_loop_freq_hz: int = 30

@RobotConfig.register_subclass("xlerobot_client")
@dataclass
class XLerobotClientConfig(RobotConfig):
    # Network Configuration
    remote_ip: str
    port_zmq_cmd: int = 5555
    port_zmq_observations: int = 5556

    teleop_keys: dict[str, str] = field(
        default_factory=lambda: {
            # Movement
            "forward": "i",
            "backward": "k",
            "left": "j",
            "right": "l",
            "rotate_left": "u",
            "rotate_right": "o",
            # Speed control
            "speed_up": "n",
            "speed_down": "m",
            # quit teleop
            "quit": "b",
        }
    )

    cameras: dict[str, CameraConfig] = field(default_factory=xlerobot_cameras_config)

    polling_timeout_ms: int = 15
    connect_timeout_s: int = 5
