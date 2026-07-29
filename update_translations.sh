#!/bin/bash

# langs=("tr" "pt" "de")
langs=("pt" "tr")

if ! command -v xgettext &> /dev/null
then
	echo "xgettext could not be found."
	echo "you can install the package with 'apt install gettext' command on debian."
	exit
fi


echo "updating pot file"
xgettext -o po/pardus-certificate-manager.pot --files-from=po/files

for lang in ${langs[@]}; do
	if [[ -f po/$lang.po ]]; then
		echo "updating $lang.po"
		msgmerge -o po/$lang.po po/$lang.po po/pardus-certificate-manager.pot
	else
		echo "creating $lang.po"
		cp po/pardus-certificate-manager.pot po/$lang.po
	fi

	# Generate .mo files for development
	echo "generating $lang.mo for development"
	mkdir -p locale/$lang/LC_MESSAGES
	msgfmt po/$lang.po -o locale/$lang/LC_MESSAGES/pardus-certificate-manager.mo
done
