import azure.functions as func

from blog_lists_api import bp as blog_lists_bp
from keyword_corrections_api import bp as keyword_corrections_bp

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

app.register_functions(blog_lists_bp)
app.register_functions(keyword_corrections_bp)
