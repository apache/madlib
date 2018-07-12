# remove symlinks created during rpm install
find $RPM_INSTALL_PREFIX/madlib/Current -depth -type l -exec rm {} \; 2>/dev/null
find $RPM_INSTALL_PREFIX/madlib/bin -depth -type l -exec rm {} \; 2>/dev/null
find $RPM_INSTALL_PREFIX/madlib/doc -depth -type l -exec rm {} \; 2>/dev/null

# remove "Versions" directory if it's empty
rmdir $RPM_INSTALL_PREFIX/madlib/Versions 2>/dev/null
