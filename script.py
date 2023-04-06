import subprocess
import datetime

format = '%Y/%m/%d %H:%M:%S.%f'

PACK = "./out/pack"  # location of pack binary

username = "edithwu"

N = 5
k = 2

labels = {"build": "build",
          "lifecycle": "lifecycleExecutor",
          "pullImage": "NetWork I/O for pulling image",
          "download": "NetWork I/O for downloading",
          "saveBuilder": "I/O for saving builder",
          "parseImageReference": "parse image reference",
          "processAppPath": "process app path",
          "processProxyConfig": "process proxy config",
          "processBuilderName": "process builder name",
          "getBuilder": "get builder",
          "resolveRunImage": "resolve run image",
          "validateRunImage": "validate run image",
          "processBuildpack": "process buildpack",
          "validateMixins": "validate mixins",
          "createEphemeralBuilder": "create ephemeral builder",
          "processVolume": "process volume",
          "getFileFilter": "get file filter",
          "translateRegistry": "translate registry",
          "stackMixins": "stack mixins",
          "allBuildpacks": "all buildpacks",
          "assembleAvailableMixins": "assemble availble mixins",
          "ensureStackSupport": "ensure stack support",
          "createNewBuilder": "create new builder",
          "addBuildpack": "add buildpack",
          "outputBuildpack": "output buildpack",
          "makeDirectoryTemp": "make directory temp",
          "getDefaultDirectoryLayer": "get default directory layer",
          "addDefaultDirectoryLayer": "add default directory layer",
          "validateBuildpacks": "validate buildpacks",
          "validateExtensions": "validate extensions",
          "getBuildpackLabel": "get buildpack label",
          "addBuildpackModule": "add buildpack module",
          "setBuildpackLabel": "set buildpack label",
          "getExtensionLabel": "get extension label",
          "addExtensionModule": "add extension module",
          "setExtensionLabel": "set extension label",
          "getStackLayer": "get stack layer",
          "addStackLayer": "add stack layer",
          "getEnvironmentLayer": "get environment layer",
          "addEnvironmentLayer": "add environment layer",
          "setMetaLabel": "set meta label",
          "setMixinsLabel": "set mixins label",
          "setWorkingDirectory": "set working directory",
          "getLifecycleLayer": "get lifecycle layer",
          "addLifecycleLayer": "add lifecycle layer",
          "processBuildpackOrder": "process buildpack order",
          "processExtensionOrder": "process extension order",
          "getOrderLayer": "get order layer",
          "addOrderLayer": "add order layer",
          "setBuildpackOrderLayer": "set buildpack order layer",
          "setExtensionOrderLayer": "set extension order layer"
          }

def run(command, out, error="error.out"):
    print(command)
    process = subprocess.Popen(command, shell=True, stdout=open(out, "w"), stderr=open(error, "w"))

    process.wait()

    output = open(out).read()
    error = open(error).read()

    if error != "":
        print(error)

    def calculateTime(label):
        time = datetime.timedelta()
        start = output.find(label + " start")
        while start != -1:
            startTime = datetime.datetime.strptime(output[output.rfind('\n', 0, start):start].strip(), format)
            end = output.find(label + " end", start)
            endTime = datetime.datetime.strptime(output[output.rfind('\n', 0, end):end].strip(), format)
            time += endTime - startTime

            # remove time spent on pulling image from validating run image
            if label == labels["validateRunImage"]:
                start = output.find(labels["pullImage"] + " start", start, end)
                if start != -1:
                    startTime = datetime.datetime.strptime(output[output.rfind('\n', 0, start):start].strip(), format)
                    end = output.find(labels["pullImage"] + " end", start)
                    endTime = datetime.datetime.strptime(output[output.rfind('\n', 0, end):end].strip(), format)
                    time -= endTime - startTime

            # remove time spent on saving builder from creating ephemeral builder
            if label == labels["createEphemeralBuilder"]:
                start = output.find(labels["saveBuilder"] + " start", start, end)
                if start != -1:
                    startTime = datetime.datetime.strptime(output[output.rfind('\n', 0, start):start].strip(), format)
                    end = output.find(labels["saveBuilder"] + " end", start)
                    endTime = datetime.datetime.strptime(output[output.rfind('\n', 0, end):end].strip(), format)
                    time -= endTime - startTime

            start = output.find(label + " start", end)

        return time

    result = {}
    for key in labels.keys():
        result[key] = calculateTime(labels[key])

    return result


def repeat(command, out):
    repeatResult = {}
    for key in labels.keys():
        repeatResult[key] = datetime.timedelta(0)
    for i in range(N):
        result = run(command, out)
        if i < k:
            continue
        else:
            for key in repeatResult.keys():
                repeatResult[key] += result[key]

    for value in repeatResult.values():
        value /= N - k
    return repeatResult


def firstBuild(imageName):
    builder = "paketobuildpacks/builder:base"
    repeatResult = {}
    for key in labels.keys():
        repeatResult[key] = datetime.timedelta(0)
    for i in range(N):
        command = PACK + " build " + imageName + "-" + datetime.datetime.now().strftime("%S.%f") + \
                  " --builder " + builder + " --timestamps -v"
        result = run(command, "first_build.out")
        if i < k:
            continue
        else:
            for key in repeatResult.keys():
                repeatResult[key] += result[key]

    for value in repeatResult.values():
        value /= N - k
    return repeatResult


def laterBuild(imageName):
    builder = "paketobuildpacks/builder:base"
    command = PACK + " build " + imageName + " --builder " + builder + " --timestamps -v"
    return repeat(command, "later_build.out")


def tinyBuild(imageName):
    builder = "paketobuildpacks/builder:tiny"
    command = PACK + " build " + imageName + " --builder " + builder + " --timestamps -v"
    return repeat(command, "tiny_build.out")


def cacheImageBuild(imageName):
    builder = "paketobuildpacks/builder:base"
    command = PACK + " build " + imageName + " --builder " + builder + \
              " --timestamps -v --cache type=build;format=image;name=paketo-demo-app;"
    return repeat(command, "cache_image_build.out")


def neverBuild(imageName):
    builder = "paketobuildpacks/builder:base"
    command = PACK + " build " + imageName + " --builder " + builder + " --pull-policy never --timestamps -v"
    return repeat(command, "never_policy_build.out")


def alwaysBuild(imageName):
    builder = "paketobuildpacks/builder:base"
    command = PACK + " build " + imageName + " --builder " + builder + " --pull-policy always --timestamps -v"
    return repeat(command, "always_policy_build.out")


def publishBuild(imageName):
    builder = "paketobuildpacks/builder:base"
    command = PACK + " build docker.io/" + username + "/" + imageName + ":latest --builder " + builder + " --publish --timestamps -v"
    return repeat(command, "publish_build.out")


def untrustedBuild(imageName):
    origin = "paketobuildpacks/builder:base"
    builder = "mybuilder:base"
    command = "docker tag " + origin + " " + builder + " && " + \
              PACK + " build " + imageName + " --builder " + builder + " --timestamps -v"
    return repeat(command, "untrusted_build.out")


def main():
    file = open("profiling.csv", "w")
    file.write("condition")
    for key in labels.keys():
        file.write(", " + key)
    file.write("\n")

    imageName = "paketo-demo-app"

    def output(taskName, result):
        file.write(taskName)
        for key in labels.keys():
            file.write(", " + str(result[key]))
        file.write("\n")

    result = firstBuild(imageName)
    output("first build", result)

    result = laterBuild(imageName)
    output("later build", result)

    result = tinyBuild(imageName)
    output("tiny build", result)

    result = cacheImageBuild(imageName)
    output("cache image build", result)

    result = neverBuild(imageName)
    output("never policy build", result)

    result = alwaysBuild(imageName)
    output("always policy build", result)

    result = publishBuild(imageName)
    output("publish build", result)

    result = untrustedBuild(imageName)
    output("untrusted build", result)

    file.close()


if __name__ == "__main__":
    main()
