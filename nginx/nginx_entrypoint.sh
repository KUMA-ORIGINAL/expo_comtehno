#!/bin/sh

get_certs_lower=$(echo "$GET_CERTS" | tr '[:upper:]' '[:lower:]')

if [ "$get_certs_lower" = "true" ]; then

    folder_path="/etc/letsencrypt/live/$DOMAIN"

    if [ -d "$folder_path" ]; then
        certbot -n --nginx --expand \
          -d "$DOMAIN" \
          -d "www.$DOMAIN" \
          -d "$NODE_DOMAIN"

        nginx -s stop
        sleep 2
    else
        certbot --nginx --expand \
          --email "$CERTBOT_EMAIL" \
          --agree-tos \
          --no-eff-email \
          -d "$DOMAIN" \
          -d "www.$DOMAIN" \
          -d "$NODE_DOMAIN"

        nginx -s stop
        sleep 2
    fi

fi