import asyncio

from nodriver.core.config import Config
import nodriver as uc

from RecaptchaSolver import RecaptchaSolver
import time


async def main():
    config = Config(
        # necessary to be able to access recaptcha iframe contents
        browser_args=["--disable-site-isolation-trials"]
    )
    driver = await uc.start(config)

    tab = await driver.get("https://www.google.com/recaptcha/api2/demo")

    recaptcha_solver = RecaptchaSolver(tab)

    t0 = time.time()
    await recaptcha_solver.solveCaptcha()
    print(f"Time to solve the captcha: {time.time() - t0:.2f} seconds")

    submit_btn = await tab.query_selector("#recaptcha-demo-submit")
    await submit_btn.click()

    await tab.close()


if __name__ == "__main__":
    asyncio.run(main())
