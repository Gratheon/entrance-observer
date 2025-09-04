while true; do
  rsync -avz --update --partial --inplace gratheon@jetson-orin:/home/gratheon/git/entrance-observer/videos ~/git/entrance-observer/remote-videos/
  sleep 10
done
