`conda activate services`

`pip install pillow`

`pip install langfuse lightrag`

`pip install -e .`

### Here's what actually worked:

1. Verified Installation: I ensured the tz_common package was correctly installed by checking the site-packages directory.

2. Extracted Egg File: I manually extracted the contents of the `tz_common-0.3-py3.10.egg` file using Python's `zipfile` module. This ensured the package's contents were accessible in the directory `c:/users/tomas/miniconda3/envs/services/lib/site-packages/tz_common`.

3. Adjusted PYTHONPATH: I added the extracted directory to the `PYTHONPATH` to make sure Python could find and import the `tz_common` module when running your script.