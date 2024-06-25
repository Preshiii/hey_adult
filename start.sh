if [ -z $UPSTREAM_REPO ]
then
  echo "Cloning main Repository"
  git clone https://github.com/Preshiii/hey_adult.git /hey_adult
else
  echo "Cloning Custom Repo from $UPSTREAM_REPO "
  git clone $UPSTREAM_REPO /hey_adult
fi
cd /hey_adult
pip3 install -U -r requirements.txt
echo "Starting hey_adult...."
python3 bot.py
