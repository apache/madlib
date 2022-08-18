# ------------------------------------------------------------------------------
# Packaging
# ------------------------------------------------------------------------------

# -- Define which package generators to use, depending on the current
#    platform ------------------------------------------------------------------

if(APPLE)
    list(APPEND CPACK_GENERATOR
        PackageMaker
    )
elseif(UNIX)
    debian_version(DEB_VERSION)
    if(DEB_VERSION AND NOT (DEB_VERSION STREQUAL "DEB_VERSION-NOTFOUND"))
      set(IS_DEBIAN "True")
    endif()
    rh_version(RH_VERSION)
    if(RH_VERSION AND NOT (RH_VERSION STREQUAL "RH_VERSION-NOTFOUND"))
      set(IS_REDHAT "True")
    endif()

    if(IS_REDHAT)
        message(STATUS "Detected RH version ${RH_VERSION}")
        list(APPEND CPACK_GENERATOR
            RPM
        )
    elseif(IS_DEBIAN)
        message(STATUS "Detected Debian version ${DEB_VERSION}")
        # By default, the cmake flag -DCREATE_RPM_FOR_UBUNTU is not
        # set to any value. The default behavior is to create a .deb
        # artifact when MADlib is compiled on Ubuntu.
        # If we instead want to create an RPM artifact for MADlib
        # on Ubuntu, then the cmake flag -DCREATE_RPM_FOR_UBUNTU can
        # be set to some value (say True), and we will only create
        # an RPM artifact on Ubuntu (i.e., we create an rpm instead
        # of the default .deb).
        # Note that package alien must already be installed for
        # building an RPM on Ubuntu.
        if(CREATE_RPM_FOR_UBUNTU)
          list(APPEND CPACK_GENERATOR
              RPM
          )
        else(CREATE_RPM_FOR_UBUNTU)
          list(APPEND CPACK_GENERATOR
              DEB
          )
        endif(CREATE_RPM_FOR_UBUNTU)
    endif()
endif()


# -- General settings for all/multiple packages generators ---------------------

if(PACKAGE_SUFFIX)
    set(_PACKAGE_SUFFIX "-${PACKAGE_SUFFIX}")
else(PACKAGE_SUFFIX)
    set(_PACKAGE_SUFFIX "")
endif(PACKAGE_SUFFIX)

set(CPACK_PACKAGE_DESCRIPTION_FILE "${CMAKE_CURRENT_SOURCE_DIR}/description.txt")
set(CPACK_PACKAGE_DESCRIPTION_SUMMARY
    "Apache MADlib is an Open-Source Library for Scalable in-Database Analytics")
set(CPACK_PACKAGE_FILE_NAME
    "madlib${_PACKAGE_SUFFIX}-${MADLIB_VERSION_STRING_NO_HYPHEN}-${CMAKE_SYSTEM_NAME}")
set(CPACK_PACKAGE_INSTALL_DIRECTORY "madlib")
set(CPACK_PACKAGE_NAME "MADlib${_PACKAGE_SUFFIX}")
set(CPACK_PACKAGE_VENDOR "Apache MADlib")
set(CPACK_PACKAGE_VERSION ${MADLIB_VERSION_STRING_NO_HYPHEN})
set(CPACK_PACKAGE_VERSION_MAJOR ${MADLIB_VERSION_MAJOR})
set(CPACK_PACKAGE_VERSION_MINOR ${MADLIB_VERSION_MINOR})
set(CPACK_PACKAGE_VERSION_PATCH ${MADLIB_VERSION_PATCH})

# CPACK_PACKAGING_INSTALL_PREFIX has to be set in the generator-specific
# section!

set(CPACK_RPM_USER_BINARY_SPECFILE ${CMAKE_CURRENT_SOURCE_DIR}/madlib.spec.in)

# -- Set settings for specific package generators ------------------------------

add_subdirectory(PackageMaker)
add_subdirectory(PGXN)
add_subdirectory(RPM)
add_subdirectory(DEB)
# gppkg depends on macros from RPM!
add_subdirectory(gppkg)


# -- Finally do the packaging! -------------------------------------------------
if(APPLE)
  set(CPACK_PREFLIGHT_SCRIPT ${CMAKE_CURRENT_SOURCE_DIR}/preflight.sh)
  set(CPACK_POSTFLIGHT_SCRIPT ${CMAKE_CURRENT_SOURCE_DIR}/postflight.sh)
  set(CPACK_MONOLITHIC_INSTALL 1)
elseif(IS_REDHAT)
  set(CPACK_RPM_POST_INSTALL_SCRIPT_FILE "${CMAKE_CURRENT_SOURCE_DIR}/rpm_post.sh")
  set(CPACK_RPM_POST_UNINSTALL_SCRIPT_FILE "${CMAKE_CURRENT_SOURCE_DIR}/rpm_post_uninstall.sh")
  set(CPACK_MONOLITHIC_INSTALL 1)
elseif(IS_DEBIAN)
  if(NOT CREATE_RPM_FOR_UBUNTU)
    set(CPACK_PACKAGE_FILE_NAME
      "madlib${_PACKAGE_SUFFIX}-${MADLIB_VERSION_STRING}-${CMAKE_SYSTEM_NAME}")
  endif(NOT CREATE_RPM_FOR_UBUNTU)
  set(CPACK_PACKAGE_VERSION ${MADLIB_VERSION_STRING})
  set(CPACK_DEBIAN_PACKAGE_CONTROL_EXTRA "${CMAKE_CURRENT_SOURCE_DIR}/DEB/config;${CMAKE_CURRENT_SOURCE_DIR}/DEB/templates;${CMAKE_CURRENT_SOURCE_DIR}/DEB/preinst;${CMAKE_CURRENT_SOURCE_DIR}/DEB/postinst;${CMAKE_CURRENT_SOURCE_DIR}/DEB/postrm")
endif()
include(CPack)


# -- We can now use CPack commands to do customization -------------------------

cpack_add_component(doc
    DISPLAY_NAME Documentation
    DESCRIPTION "API reference and documentation (generated with Doxygen)."
)

cpack_add_component(core
    DISPLAY_NAME "Madlib Core"
    DESCRIPTION "DBMS-independent files installed with every MADlib installation."
    REQUIRED
)

cpack_add_component_group(ports
    DISPLAY_NAME "DBMS-Specific Components"
    DESCRIPTION "DBMS-specific files and libraries."
    EXPANDED
)

file(GLOB PORT_COMPONENTS "${CMAKE_CURRENT_BINARY_DIR}/Component_*.cmake")
foreach(PORT_COMPONENT ${PORT_COMPONENTS})
    include("${PORT_COMPONENT}")
endforeach(PORT_COMPONENT)

