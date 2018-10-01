# coding=utf-8
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

##############################################################
#### During RPM upgrade, rpm_post.sh is run first, followed by
## rpm_post_uninstall.sh. So we must do all the uninstallation specific stuff
## based on the current operation being uninstall or upgrade.

# If the first argument to %preun and %postun is 1, the action is an upgrade
# If the first argument to %preun and %postun is 0, the action is uninstallation
##############################################################
if [ "$1" = "0" ]; then
    # remove symlinks created during rpm install
    find $RPM_INSTALL_PREFIX/madlib/Current -depth -type l -exec rm {} \; 2>/dev/null
    find $RPM_INSTALL_PREFIX/madlib/bin -depth -type l -exec rm {} \; 2>/dev/null
    find $RPM_INSTALL_PREFIX/madlib/doc -depth -type l -exec rm {} \; 2>/dev/null

    # remove "Versions" directory if it's empty
    if [ -d $RPM_INSTALL_PREFIX/madlib/Versions ]; then
        rmdir $RPM_INSTALL_PREFIX/madlib/Versions 2>/dev/null
    fi
fi
