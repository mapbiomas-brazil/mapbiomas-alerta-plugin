#!/bin/bash
plugin_dir=$( basename $( pwd ) )
if [ -f "./$plugin_dir.zip" ]; then
  rm "./$plugin_dir.zip"
fi
mkdir "./$plugin_dir"
cp *.py "./$plugin_dir"
cp *.png "./$plugin_dir"
cp *.qml "./$plugin_dir"
cp *.ui "./$plugin_dir"
for item in metadata.txt LICENSE territory_bbox.csv; do cp "./$item" "./$plugin_dir"; done
zip -r $plugin_dir $plugin_dir
rm -r $plugin_dir
#
kdialog --msgbox "Zip file created: "$plugin_dir".zip"
