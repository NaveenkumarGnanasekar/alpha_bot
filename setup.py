import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'alpha_bot'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', 'alpha_bot', 'launch'), glob('launch/*.py')),
        (os.path.join('share', 'alpha_bot', 'urdf'), glob('urdf/*')),
        (os.path.join('share', 'alpha_bot', 'config'),glob('config/*')),
        (os.path.join('share', 'alpha_bot', 'map'),glob('map/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='naveen',
    maintainer_email='naveen@todo.todo',
    description='TODO: Package description',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            "circular_motion = alpha_bot.circular_motion:main",
            "llm_commander = alpha_bot.llm_commander:main",
            "text_input = alpha_bot.text_input:main",
            "voice_input = alpha_bot.voice_input:main",
            "waypoint_teacher = alpha_bot.waypoint_teacher:main",
        ],
    },
)
