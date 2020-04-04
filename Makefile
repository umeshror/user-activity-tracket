build:
	docker build -t se-service .
run:
	docker run -p 5000:5000 se-service:latest
dev:
	docker run -p 5000:5000 --mount src=`pwd`/service,target=/se/service,type=bind -e "FLASK_DEBUG=True" se-service:latest



