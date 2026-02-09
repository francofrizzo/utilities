from setuptools import setup, find_packages

setup(
    name="print-label",
    version="0.4.0",
    description="Thermal printer label maker for Bluetooth cat printers",
    author="Franco Frizzo",
    license="MIT",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    entry_points={
        "console_scripts": [
            "print-label=print_label.cli:main",
        ],
    },
    install_requires=[
        "bleak>=0.20",
        "Pillow>=9.0",
        "numpy<2.0",
        "opencv-python<5.0",
    ],
    python_requires=">=3.8",
)
