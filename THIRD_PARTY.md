# Reused components

Dependencies are installed by the user, not vendored into the source ZIP. Their complete licenses and transitive dependencies accompany the installed distributions. `requirements.lock` records the tested versions.

| Component | Use | Official source |
|---|---|---|
| Python / SQLite | runtime, local persistence | https://www.python.org/ / https://www.sqlite.org/ |
| FastAPI / Starlette / Pydantic | HTTP and validation | https://github.com/fastapi/fastapi / https://github.com/Kludex/starlette / https://github.com/pydantic/pydantic |
| uvicorn | local ASGI server | https://github.com/Kludex/uvicorn |
| scikit-learn | TF-IDF and cosine similarity | https://scikit-learn.org/ |
| NumPy / SciPy | sparse numerical operations | https://numpy.org/ / https://scipy.org/ |
| httpx | offline HTTP test client | https://www.python-httpx.org/ |

Character n-gram retrieval uses the documented `TfidfVectorizer` and `cosine_similarity` APIs. No custom ML model is trained. Demo notes are newly generated synthetic examples. No fonts, icons, datasets, images or competitor works were downloaded into this app.
