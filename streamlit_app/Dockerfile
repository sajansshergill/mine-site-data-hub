FROM python:3.11-slim
WORKDIR /app
COPY streamlit_app/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY streamlit_app /app/streamlit_app
COPY .streamlit /app/.streamlit
ENV MINEHUB_API_URL=http://api:8000
ENV MINEHUB_API_KEY=viewer-key
EXPOSE 8501
CMD ["streamlit", "run", "streamlit_app/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
