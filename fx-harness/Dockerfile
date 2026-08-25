FROM alpine:3.20 AS builder
RUN apk add --no-cache wget tar xz

RUN wget https://ziglang.org \
    && tar -xf zig-linux-x86_64-0.13.0.tar.xz \
    && mv zig-linux-x86_64-0.13.0 /usr/local/share/zig \
    && ln -s /usr/local/share/zig/zig /usr/bin/zig

WORKDIR /app
COPY . .

RUN zig build -Doptimize=ReleaseSmall

FROM scratch
COPY --from=builder /app/zig-out/bin/fx-lightweight /fx-agent

ENTRYPOINT ["/fx-agent"]
