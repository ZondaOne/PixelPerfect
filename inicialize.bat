@echo off 
REM Cambia a la carpeta raíz del proyecto (ajustá la ruta si es necesario)
cd /d "C:\Users\Bruno\Desktop\zonda-pixel_perfect"

echo Iniciando RabbitMQ...
docker start some-rabbit

echo Iniciando Backend...
start cmd /k "cd backend && call mvnw.cmd spring-boot:run"

echo Iniciando Microservicio bg-removal-service...
start cmd /k "cd microservices\bg-removal-service && call .venv\Scripts\activate.bat && uvicorn app.main:app --host 0.0.0.0 --port 8001"

echo Iniciando Microservicio upscaling-service...
start cmd /k "cd microservices\upscaling-service && call .venv\Scripts\activate.bat && uvicorn app.main:app --host 0.0.0.0 --port 8002"


echo Iniciando Microservicio enlarge-service...
start cmd /k "cd microservices\enlarge-service && call .venv\Scripts\activate.bat && uvicorn app.main:app --host 0.0.0.0 --port 8003"

echo Iniciando Microservicio object remover...
start cmd /k "cd microservices\object-remover-service && call .venv\Scripts\activate.bat && uvicorn app.main:app --host 0.0.0.0 --port 8004"

echo Iniciando Microservicio image  generation ...
start cmd /k "cd microservices\image-generation-service && call .venv\Scripts\activate.bat && uvicorn app.main:app --host 0.0.0.0 --port 8007"




echo Esperando 15 segundos para que el backend arranque...
timeout /t 15 /nobreak

echo Iniciando Frontend...
start cmd /k "cd frontend && yarn start"

echo Todos los servicios iniciados!
pause
