FROM nginx:1.13.3

# Copy the Nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Expose website on port
EXPOSE 80
EXPOSE 443

CMD ["nginx", "-g", "daemon off;"]
