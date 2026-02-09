from setuptools import setup, find_packages

setup(
    name="print-label",
    version="0.1.0",
    description="Thermal printer label maker for Bluetooth cat printers",
    author="Franco Frizzo",
    license="MIT",
    packages=find_packages(where="lib"),
    package_dir={"": "lib"},
    scripts=["bin/print-label"],
    install_requires=[
        "bleak>=0.20",
        "Pillow>=9.0",
        "numpy<2.0",
        "opencv-python<5.0",
    ],
    python_requires=">=3.8",
)
