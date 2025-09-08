while true; do
  rsync -avz --update --partial --inplace --exclude '*_detect.mp4' gratheon@jetson-orin:/home/gratheon/git/videos2 ~/git/entrance-observer/remote-videos/
  sleep 10
done
