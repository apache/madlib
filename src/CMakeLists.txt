# ------------------------------------------------------------------------------
# MADlib CMake Build Script
# ------------------------------------------------------------------------------

# -- Paths and MD5 hashes of third-party downloadable source code (third-party
#    components needed only by specific ports are downloaded there) ------------

set(MADLIB_REDIRECT_PREFIX "")

if(NOT GPPKG_VER)
    set(GPPKG_VER '')
endif (NOT GPPKG_VER)

# For in-house testing, we might want to change the base URLs of code-hosting
# sites to something local
# "-DSOURCEFORGE_BASE_URL=http://test.local/projects"
set(SOURCEFORGE_BASE_URL
    "${MADLIB_REDIRECT_PREFIX}http://sourceforge.net/projects"
    CACHE STRING
    "Base URL for Sourceforge projects. May be overridden for testing purposes.")
set(BITBUCKET_BASE_URL
    "${MADLIB_REDIRECT_PREFIX}https://bitbucket.org"
    CACHE STRING
    "Base URL for Bitbucket projects. May be overridden for testing purposes.")
set(EIGEN_BASE_URL
    "${MADLIB_REDIRECT_PREFIX}https://github.com/madlib/eigen/archive"
    CACHE STRING
    "Base URL for Eigen projects. May be overridden for testing purposes.")

# Boost might not be present on the system (or simply too old). In this case, we
# download the following version (unless it is already present in
# ${CMAKE_CURRENT_BINARY_DIR}/third_party/downloads).
# It is also possible to specify an alternative path to the Boost tarball when
# running cmake:
# "-DBOOST_TAR_SOURCE=/path/to/boost_x_x_x.tar.gz"

if (CXX11)
    set(BOOST_TAR_VERSION "1.75.0")  # If CXX11 is enabled, we can use latest version of Boost
    set(BOOST_TAR_MD5 38813f6feb40387dfe90160debd71251)
else(CXX11)
    set(BOOST_TAR_VERSION "1.61.0")   # Most recent version that includes TR1 (necessary for old C++ compilers)
    set(BOOST_TAR_MD5 874805ba2e2ee415b1877ef3297bf8ad)
endif(CXX11)
    string(REPLACE "." "_" _BOOST_TAR_VERSION_UNDERSCORES ${BOOST_TAR_VERSION})
    set(BOOST_TAR "boost_${_BOOST_TAR_VERSION_UNDERSCORES}.tar.gz")
    set(BOOST_URL "${SOURCEFORGE_BASE_URL}/boost/files/${BOOST_TAR}")

if(NOT BOOST_TAR_SOURCE)
    find_file(BOOST_TAR_SOURCE ${BOOST_TAR}  # If not user-specified, try finding in downloads dir
        PATHS ${MAD_THIRD_PARTY}/downloads)

    if (NOT BOOST_TAR_SOURCE)
        set(BOOST_TAR_SOURCE ${BOOST_URL})   # If not found locally, download
    endif()
endif(NOT BOOST_TAR_SOURCE)

# We always download Eigen (unless it is already present in
# ${CMAKE_CURRENT_BINARY_DIR}/third_party/downloads). It is also possible to
# specify an alternative path to the Eigen tarball:
# -DEIGEN_TAR_SOURCE=/path/to/eigen-x.x.x.tar.gz

set(EIGEN_VERSION "branches/3.2")
set(EIGEN_URL "${EIGEN_BASE_URL}/${EIGEN_VERSION}.tar.gz")
set(EIGEN_TAR_MD5 13bc1043270d8f4397339c0cb0b62938)
set(EIGEN_MPL2_ONLY TRUE)

if(NOT EIGEN_TAR_SOURCE)
    STRING(REGEX REPLACE "/" "-" EIGEN_VERSION_NO_SLASH ${EIGEN_VERSION})
    set(EIGEN_TAR "eigen-${EIGEN_VERSION_NO_SLASH}.tar.gz")   # eigen-branches-3.2.tar.gz
    find_file(EIGEN_TAR_SOURCE ${EIGEN_TAR}
              PATHS ${MAD_THIRD_PARTY}/downloads)
endif(NOT EIGEN_TAR_SOURCE)

if(NOT EIGEN_TAR_SOURCE)
    set(EIGEN_TAR_SOURCE ${EIGEN_URL})
endif (NOT EIGEN_TAR_SOURCE)

# We always download PyXB (unless it is already present in
# ${CMAKE_CURRENT_BINARY_DIR}/third_party/downloads). It is also possible to
# specify an alternative path to the PyXB tarball:
# -DPYXB_TAR_SOURCE=/path/to/PyXB-x.x.x.tar.gz

set(PYXB_VERSION "1.2.6")
set(PYXB_TAR_MD5 4303573fc7094ce4664c5b71cd4bdb48)

set(PYXB_TAR "PyXB-${PYXB_VERSION}.tar.gz")
set(PYXB_URL "${SOURCEFORGE_BASE_URL}/pyxb/files/${PYXB_TAR}")

if(NOT PYXB_TAR_SOURCE)
    find_file(PYXB_TAR_SOURCE ${PYXB_TAR}
        PATHS ${MAD_THIRD_PARTY}/downloads)
endif(NOT PYXB_TAR_SOURCE)

if(NOT PYXB_TAR_SOURCE)
    set(PYXB_TAR_SOURCE ${PYXB_URL})
endif (NOT PYXB_TAR_SOURCE)

# -- Local definitions (filenames, paths, etc.) --------------------------------

set(MAD_PATCH_DIR ${CMAKE_CURRENT_BINARY_DIR}/patch)

set(MAD_MODULE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/modules)


# ==============================================================================
# From here on, modifications should rarely be necessary.
# In other words: Be careful when you make changes. You have been warned. Don't
# try this at home.
# ==============================================================================

# -- Third-party dependencies: Download the Boost if not previously detected
if(Boost_FOUND)
    message(STATUS "Boost include directory ${Boost_INCLUDE_DIRS}")
    include_directories(${Boost_INCLUDE_DIRS})
else(Boost_FOUND)
    ExternalProject_Add(EP_boost
        PREFIX ${MAD_THIRD_PARTY}
        DOWNLOAD_DIR ${MAD_THIRD_PARTY}/downloads
        URL ${BOOST_TAR_SOURCE}
        URL_MD5 ${BOOST_TAR_MD5}
        CMAKE_COMMAND /usr/bin/env echo Ignored: cmake
        BUILD_COMMAND /usr/bin/env echo Ignored: make
        INSTALL_COMMAND /usr/bin/env echo Ignored: make
        BINARY_DIR ${MAD_THIRD_PARTY}/src/EP_boost
    )
    include_directories(BEFORE SYSTEM ${MAD_THIRD_PARTY}/src/EP_boost)
endif(Boost_FOUND)

# -- Third-party dependencies: Download the C++ linear-algebra library Eigen ---
ExternalProject_Add(EP_eigen
    PREFIX ${MAD_THIRD_PARTY}
    DOWNLOAD_DIR ${MAD_THIRD_PARTY}/downloads
    URL ${EIGEN_TAR_SOURCE}
    CMAKE_COMMAND /usr/bin/env echo Ignored: cmake
    BUILD_COMMAND /usr/bin/env echo Ignored: make
    INSTALL_COMMAND /usr/bin/env echo Ignored: make
    BINARY_DIR ${MAD_THIRD_PARTY}/src/EP_eigen
)

include_directories(SYSTEM ${MAD_THIRD_PARTY}/src/EP_eigen)


# -- Third-party dependencies: Download the Python libraries ---

find_package(PythonInterp REQUIRED)

set(BUILD_PYTHON_LIBDIR "${CMAKE_BINARY_DIR}/src/lib/python")

ExternalProject_Add(EP_pyxb
    PREFIX ${MAD_THIRD_PARTY}
    DOWNLOAD_DIR ${MAD_THIRD_PARTY}/downloads
    URL ${PYXB_TAR_SOURCE}
    URL_MD5 ${PYXB_TAR_MD5}
    PATCH_COMMAND "${CMAKE_CURRENT_SOURCE_DIR}/patch/PyXB.sh"
    CONFIGURE_COMMAND ""
    SOURCE_DIR ${MAD_THIRD_PARTY}/src/EP_pyxb
    BUILD_COMMAND ""
    BUILD_IN_SOURCE 1
    INSTALL_COMMAND ${PYTHON_EXECUTABLE} setup.py install --install-lib ${BUILD_PYTHON_LIBDIR} > /dev/null
)

install(DIRECTORY ${BUILD_PYTHON_LIBDIR}
    DESTINATION lib
    COMPONENT core
    FILES_MATCHING PATTERN "*.py"
)


# -- Macros to be used by ports ------------------------------------------------

# Get the architectures in a Mac OS X binary
macro(osx_archs FILENAME OUT_ARCHS)
    execute_process(
        COMMAND /usr/bin/lipo -info ${FILENAME}
        OUTPUT_VARIABLE _LIPO_OUTPUT)
    string(REPLACE "\n" "" _LIPO_OUTPUT ${_LIPO_OUTPUT})
    string(REGEX REPLACE ".*:[ ]*([^ ].*[^ ])[ ]*\$" "\\1" ${OUT_ARCHS} "${_LIPO_OUTPUT}")
    string(REPLACE " " ";" ${OUT_ARCHS} ${${OUT_ARCHS}})
endmacro(osx_archs)

# Add Python files to be preprocessed with m4
macro(add_python_files OUT_PYTHON_TARGET_FILES IN_SOURCE_DIR IN_TARGET_DIR)
    set(IN_M4_ARGUMENTS ${ARGN})

    get_filename_component(SOURCE_DIR_ABS "${IN_SOURCE_DIR}" ABSOLUTE)
    get_filename_component(TARGET_DIR_ABS "${IN_TARGET_DIR}" ABSOLUTE)
    file(GLOB_RECURSE PYTHON_FILES
        RELATIVE "${SOURCE_DIR_ABS}"
        "${SOURCE_DIR_ABS}/*.py_in"
    )
    set(MADLIB_PYTHON_M4_PREPROCESSING
        COMMAND ${CMAKE_COMMAND} -E make_directory "\"\${OUTDIR}\""
        COMMAND ${M4_BINARY} ${M4_ARGUMENTS} ${IN_M4_ARGUMENTS}
            "\"\${CURRENT_PATH}\"" > "\"\${OUTFILE}\""
    )
    batch_add_command(
        TARGET_PREFIX "${TARGET_DIR_ABS}/"
        SOURCE_PREFIX "${SOURCE_DIR_ABS}/"
        TARGET_SUFFIX ".py"
        SOURCE_SUFFIX "[.]py_in"
        RUN "${MADLIB_PYTHON_M4_PREPROCESSING}"
        COMMENT "Preprocessing \${CURRENT_FILE} with m4."
        TARGET_FILE_LIST_REF ${OUT_PYTHON_TARGET_FILES}
        SOURCE_FILE_LIST ${PYTHON_FILES}
    )
endmacro(add_python_files)

# Add sql files to be copied
macro(add_sql_files OUT_SQL_TARGET_FILES IN_SOURCE_DIR IN_TARGET_DIR)
    get_filename_component(SOURCE_DIR_ABS "${IN_SOURCE_DIR}" ABSOLUTE)
    get_filename_component(TARGET_DIR_ABS "${IN_TARGET_DIR}" ABSOLUTE)
    file(GLOB_RECURSE SQL_FILES
        RELATIVE "${SOURCE_DIR_ABS}"
        "${SOURCE_DIR_ABS}/*.sql_in"
    )
    # psql of PostgreSQL < 9 does not like byte-order marks
    set(_MADLIB_VERIFY_AND_COPY_COMMAND
        # COMMAND "${CMAKE_SOURCE_DIR}/cmake/TestIfNoUTF8BOM.py" "\"\${CURRENT_PATH}\""
        COMMAND "${CMAKE_COMMAND}" -E copy "\"\${CURRENT_PATH}\"" "\"\${OUTFILE}\""
    )
    batch_add_command(
        TARGET_PREFIX "${TARGET_DIR_ABS}/"
        SOURCE_PREFIX "${SOURCE_DIR_ABS}/"
        TARGET_SUFFIX ""
        SOURCE_SUFFIX ""
        RUN "${_MADLIB_VERIFY_AND_COPY_COMMAND}"
        COMMENT "Validating and copying \${CURRENT_FILE}."
        TARGET_FILE_LIST_REF ${OUT_SQL_TARGET_FILES}
        SOURCE_FILE_LIST ${SQL_FILES}
    )
endmacro(add_sql_files)

# Add a connector library for a specific DBMS port
macro(add_madlib_connector_library IN_TARGET_NAME IN_LIB_DIR IN_LIB_LOADER)
    set(IN_LIBRARY_SOURCES ${ARGN})

    add_library(
        ${IN_TARGET_NAME}
        MODULE
        ${IN_LIBRARY_SOURCES}
    )
    add_dependencies(${IN_TARGET_NAME} EP_eigen)
    set_target_properties(${IN_TARGET_NAME} PROPERTIES
        LIBRARY_OUTPUT_DIRECTORY "${IN_LIB_DIR}"
        OUTPUT_NAME "madlib"
        BUILD_WITH_INSTALL_RPATH YES
    )

    if(APPLE)
        set_target_properties(${IN_TARGET_NAME} PROPERTIES
            LINK_FLAGS
            "-Wl,-unexported_symbols_list,${CMAKE_CURRENT_SOURCE_DIR}/../../../unexported_symbols_list.txt -bundle_loader \"${IN_LIB_LOADER}\"")
    endif(APPLE)

    if((NOT APPLE))
        set_target_properties(${IN_TARGET_NAME} PROPERTIES
            LINK_FLAGS
            "-Wl,--version-script=${CMAKE_CURRENT_SOURCE_DIR}/../../../library.ver")
    endif((NOT APPLE))
endmacro(add_madlib_connector_library)


# -- Speciy files that will be compiled into MADlib core library ---------------

# FIXME: The CMake description of file(GLOB ...) says:
# "We do not recommend using GLOB to collect a list of source files from your
# source tree. If no CMakeLists.txt file changes when a source is added or
# removed then the generated build system cannot know when to ask CMake to
# regenerate."
# We still use GLOB here because we think the benefits outweigh the mentioned
# disadvantage.

file(GLOB_RECURSE MAD_CPP_SOURCES
    dbal/*.hpp
    modules/*.cpp modules/*.hpp
    utils/*.hpp
)
list(APPEND MAD_SOURCES
    ${MAD_CPP_SOURCES}
)
file(GLOB_RECURSE MAD_STEMMER_SOURCES
    libstemmer/*
)
list(APPEND MAD_SOURCES
    ${MAD_STEMMER_SOURCES}
)
if((NOT APPLE) AND LIBSTDCXX_COMPAT AND CMAKE_COMPILER_IS_GNUCXX)
    if(GNUCXX_VERSION VERSION_GREATER 4.1.2)
        math(EXPR LIBSTDCXX_COMPAT_MAJOR "${LIBSTDCXX_COMPAT} / 10000")
        math(EXPR LIBSTDCXX_COMPAT_MINOR "(${LIBSTDCXX_COMPAT} / 100) % 100")
        math(EXPR LIBSTDCXX_COMPAT_PATCH "${LIBSTDCXX_COMPAT} % 100")
        set(LIBSTDCXX_COMPAT_VERSION "${LIBSTDCXX_COMPAT_MAJOR}.${LIBSTDCXX_COMPAT_MINOR}.${LIBSTDCXX_COMPAT_PATCH}")
        message(STATUS "Compatibility with libstdc++ of g++ "
            "${LIBSTDCXX_COMPAT_VERSION} requested (current g++ version is "
            "${GNUCXX_VERSION}).")
        message(STATUS "If this does not work, try option INCLUDE_LIBSTDCXX "
            "instead, in order to redistribute the build-time libstdc++.")
        list(APPEND MAD_SOURCES
            "${CMAKE_CURRENT_SOURCE_DIR}/utils/libstdcxx-compatibility.cpp")
        add_definitions("-DLIBSTDCXX_COMPAT=${LIBSTDCXX_COMPAT}")
    endif(GNUCXX_VERSION VERSION_GREATER 4.1.2)
endif((NOT APPLE) AND LIBSTDCXX_COMPAT AND CMAKE_COMPILER_IS_GNUCXX)

include_directories(${CMAKE_CURRENT_SOURCE_DIR})


if(CMAKE_COMPILER_IS_GNUCXX)
    if(GNUCXX_VERSION VERSION_GREATER 4.4 OR GNUCXX_VERSION VERSION_EQUAL 4.4)
        if(INCLUDE_LIBSTDCXX)
            # FIXME: The following only takes care of the symbolic link
            # Need to implement copying of files containing version numbers in
            # file name

            # Both CentOS/RH 5 ship with old versions of libstdc++
            # Starging with gcc 4.4, C++ code may therefore not run any more on
            # vanilla installations of CentOS/RH 5. We therefore include libstdc++
            # in this case and install it in $MADLIB_ROOT/lib
            set(_LIBSTDCXX_FILENAME
                "${CMAKE_SHARED_LIBRARY_PREFIX}stdc++${CMAKE_SHARED_LIBRARY_SUFFIX}")
            execute_process(
                COMMAND ${CMAKE_C_COMPILER}
                    "-print-file-name=${_LIBSTDCXX_FILENAME}"
                OUTPUT_VARIABLE _LIBSTDCXX_PATH
                OUTPUT_STRIP_TRAILING_WHITESPACE)
            add_custom_command(
                OUTPUT
                    "${CMAKE_CURRENT_BINARY_DIR}/lib/${_LIBSTDCXX_FILENAME}"
                COMMAND "${CMAKE_COMMAND}" -E copy ${_LIBSTDCXX_PATH}
                    "${CMAKE_CURRENT_BINARY_DIR}/lib/${_LIBSTDCXX_FILENAME}"
                COMMENT "Copying libstdc++ to lib directory."
                )
            add_custom_target(copyLibStdCXX ALL DEPENDS
                "${CMAKE_CURRENT_BINARY_DIR}/lib/${_LIBSTDCXX_FILENAME}")
        endif(INCLUDE_LIBSTDCXX)

        # Also install it
        install(DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/lib
            DESTINATION .
            COMPONENT core
            FILES_MATCHING REGEX "^.*/[^/]*stdc\\+\\+[^/]*\$"
        )
    endif(GNUCXX_VERSION VERSION_GREATER 4.4 OR GNUCXX_VERSION VERSION_EQUAL 4.4)
endif(CMAKE_COMPILER_IS_GNUCXX)


# -- Preprocess/copy all Python/SQL files --------------------------------------

add_python_files(
    PYTHON_TARGET_FILES
    "modules"
    "${CMAKE_CURRENT_BINARY_DIR}/modules"
)
add_custom_target(pythonFiles ALL DEPENDS ${PYTHON_TARGET_FILES})

add_sql_files(
    SQL_TARGET_FILES
    "modules"
    "${CMAKE_CURRENT_BINARY_DIR}/modules"
)
add_custom_target(sqlFiles ALL DEPENDS ${SQL_TARGET_FILES})

# -- Use all necessary patches directory ---------------------------------------

include_directories(BEFORE "${MAD_PATCH_DIR}")


# -- Add subdirectories --------------------------------------------------------

add_subdirectory(patch)
add_subdirectory(bin)
add_subdirectory(config)
add_subdirectory(madpack)
add_subdirectory(ports)
