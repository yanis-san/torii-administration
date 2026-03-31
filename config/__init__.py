# Fix for Python 3.14 threading issue with _strptime module
# This must be imported before any date parsing happens in Django
import _strptime
