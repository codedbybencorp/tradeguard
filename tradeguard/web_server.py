"""Entry point to launch the TradeGuard web dashboard."""

import uvicorn

from tradeguard.web import app


def main() -> None:
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
