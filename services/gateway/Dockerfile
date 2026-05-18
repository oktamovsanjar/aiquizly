FROM golang:1.22-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
COPY vendor/ ./vendor/
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -mod=vendor -o /gateway ./cmd/main.go

FROM alpine:3.19
RUN apk --no-cache add ca-certificates wget
COPY --from=builder /gateway /gateway
EXPOSE 8080
CMD ["/gateway"]
