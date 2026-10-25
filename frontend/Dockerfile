# Usamos una imagen ligera de Nginx para servir los archivos estáticos
FROM nginx:alpine

# Copiar todo el contenido de la carpeta frontend al directorio por defecto de Nginx
COPY . /usr/share/nginx/html

# Exponer el puerto 80
EXPOSE 80

# Iniciar Nginx en primer plano
CMD ["nginx", "-g", "daemon off;"]