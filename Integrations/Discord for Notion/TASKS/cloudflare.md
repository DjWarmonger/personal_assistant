#### 2. Wystawienie endpointu przez Cloudflare Tunnel

1. **Zainstaluj Cloudflare Tunnel (cloudflared)** na PC:
   Sprawdź aktualną instalację cloudflared:
   ```bash
   cloudflared --version
   ```

   Sprawdx obecną konfigurację:
   ```bash
   cloudflared tunnel list
   ```

2. **Zaloguj się**:
   `cloudflared tunnel login` – otworzy przeglądarkę, dodasz serwer do swojego konta CF.
3. **Utwórz tunel**:

   ```bash
   cloudflared tunnel create agent-tunnel
   cloudflared tunnel route dns agent-tunnel agent.example.com
   ```
4. **Konfiguracja YAML** (`~/.cloudflared/config.yml`):

   ```yaml
   tunnel: agent-tunnel
   credentials-file: /home/you/.cloudflared/agent-tunnel.json
   ingress:
     - hostname: agent.example.com
       service: http://localhost:8080
     - service: http_status:404
   ```
5. **Start**: `cloudflared tunnel run agent-tunnel`
   Teraz `https://agent.example.com` przekierowuje do twojego kontenera lokalnie.

-