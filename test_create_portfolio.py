import asyncio
import httpx

async def main():
    async with httpx.AsyncClient() as client:
        # try to register
        res = await client.post("http://localhost:8000/api/v1/auth/register", json={"username": "testuser", "email": "testuser@example.com", "password": "password"})
        print("register", res.status_code, res.text)
        resp = await client.post("http://localhost:8000/api/v1/auth/token", data={"username": "testuser", "password": "password"})
        print("login", resp.status_code, resp.text)
        
        if resp.status_code == 200:
            token = resp.json()["access_token"]
            
            # 2. create portfolio
            resp = await client.post("http://localhost:8000/api/v1/portfolios", json={"name": "Test Portfolio", "base_currency": "USD", "color_hex": "#000000"}, headers={"Authorization": f"Bearer {token}"})
            print("create portfolio", resp.status_code, resp.text)

asyncio.run(main())
