from django.http import HttpResponse
from django.shortcuts import render

from . import services

MAX_FILE_SIZE = 1_000_000


def read_uploaded_file(uploaded):
    if uploaded.size > MAX_FILE_SIZE:
        raise ValueError("Файл завеликий: максимум 1 МБ.")
    try:
        content = uploaded.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError("Файл не є коректним UTF-8.")
    return content.replace("\r\n", "\n")


def read_form(request):
    return {
        "language": request.POST.get("language", "uk"),
        "algorithm": request.POST.get("algorithm", "coordinates"),
        "operation": request.POST.get("operation", "encrypt"),
        "key": request.POST.get("key", ""),
        "text": request.POST.get("text", "").replace("\r\n", "\n"),
        "strip_spaces": request.POST.get("strip_spaces") == "on",
    }


def index(request):
    form = {"language": "uk", "algorithm": "coordinates", "operation": "encrypt",
            "key": "", "text": "", "strip_spaces": False}
    context = {"error": None, "result": None, "square_rows": None}

    if request.method == "POST":
        form = read_form(request)
        try:
            uploaded = request.FILES.get("file")
            if uploaded:
                form["text"] = read_uploaded_file(uploaded)
            result = services.process(
                form["language"], form["algorithm"], form["operation"],
                form["key"], form["text"], form["strip_spaces"],
            )
        except ValueError as error:
            context["error"] = str(error)
        else:
            if request.POST.get("action") == "download":
                response = HttpResponse(result, content_type="text/plain; charset=utf-8")
                response["Content-Disposition"] = 'attachment; filename="result.txt"'
                return response
            context["result"] = result

        if form["algorithm"] != "gronsfeld":
            try:
                square = services.make_square(form["language"], form["key"])
                context["square_rows"] = list(enumerate(square, start=1))
            except ValueError:
                pass  # причину вже показано в context["error"]

    context.update({
        "form": form,
        "languages": services.LANGUAGES,
        "algorithms": services.ALGORITHMS,
        "operations": services.OPERATIONS,
    })
    return render(request, "polybius_gronsfeld/index.html", context)
