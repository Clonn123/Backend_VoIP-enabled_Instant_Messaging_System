Всегда должен быть запущен Docker Desktop

1) В первый раз собрать контейнеры docker-compose up --build
2) В дальнейшем, если не менялись requirements.txt или Dockerfile, то просто запуска контейнеров docker-compose up
3) Если необходимо удалить все контейнеры и образы в случае необходимости, то docker-compose down --rmi all --volumes (ну или через сам докер вручную)