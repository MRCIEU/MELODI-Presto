#!/bin/bash

# Start Gunicorn processes
echo Starting Gunicorn.

#make sure we are at project root /usr/src/app
cd $PROJECT_ROOT

if [ ! -f $PROJECT_ROOT/.build ]; then
  echo "Collecting statics files"
  pushd django_project
  python manage.py collectstatic --noinput
  popd
  date > $PROJECT_ROOT/.build
fi

cd django_project // Change to our Django project
exec gunicorn django_project.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 5 \
    --timeout 600
