import subprocess
import datetime

format = '%Y/%m/%d %H:%M:%S.%f'

PACK = "./out/pack" # location of pack binary

def run(command):
    print(command)
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    process.wait()

    output = process.stdout.read().decode(encoding="gbk")
    error = process.stderr.read().decode(encoding="gbk")

    if error != "":
        print(error)

    start = output.find("build start")
    startTime = datetime.datetime.strptime(output[output.rfind('\n', 0, start):start].strip(), format)
    end = output.find("build end")
    endTime = datetime.datetime.strptime(output[output.rfind('\n', 0, end):end].strip(), format)
    buildTime = endTime - startTime

    start = output.find("lifecycleExecutor start")
    startTime = datetime.datetime.strptime(output[output.rfind('\n', 0, start):start].strip(), format)
    end = output.find("lifecycleExecutor end")
    endTime = datetime.datetime.strptime(output[output.rfind('\n', 0, end):end].strip(), format)
    lifecycleTime = endTime - startTime

    start = output.find("fetchBuilder start")
    startTime = datetime.datetime.strptime(output[output.rfind('\n', 0, start):start].strip(), format)
    end = output.find("fetchBuilder end")
    endTime = datetime.datetime.strptime(output[output.rfind('\n', 0, end):end].strip(), format)
    fetchBuilderTime = endTime - startTime

    start = output.find("fetchBuildpack start")
    startTime = datetime.datetime.strptime(output[output.rfind('\n', 0, start):start].strip(), format)
    end = output.find("fetchBuildpack end")
    endTime = datetime.datetime.strptime(output[output.rfind('\n', 0, end):end].strip(), format)
    fetchBuildpackTime = endTime - startTime

    return {"build": buildTime, "lifecycle": lifecycleTime, "fetchBuilder": fetchBuilderTime, "fetchBuildpack": fetchBuildpackTime}


def laterBuild(imageName):
    builder = "paketobuildpacks/builder:base"
    command = PACK + " build " + imageName + " --builder " + builder + " --timestamps -v"
    return run(command)


def tinyBuild(imageName):
    builder = "paketobuildpacks/builder:tiny"
    command = PACK + " build " + imageName + " --builder " + builder + " --timestamps -v"
    return run(command)


def neverBuild(imageName):
    builder = "paketobuildpacks/builder:base"
    command = PACK + " build " + imageName + " --builder " + builder + " --pull-policy never --timestamps -v"
    return run(command)


def alwaysBuild(imageName):
    builder = "paketobuildpacks/builder:base"
    command = PACK + " build " + imageName + " --builder " + builder + " --pull-policy always --timestamps -v"
    return run(command)


def main():
    file = open("profiling.csv", "w")
    file.write("condition, build, lifecycle, fetchBuilder, fetchBuildpack\n")

    imageName = "paketo-demo-app"

    result = laterBuild(imageName)
    file.write("later build, " + str(result["build"]) + ", " + str(result["lifecycle"]) + ", " +
               str(result["fetchBuilder"]) + ", " + str(result["fetchBuildpack"]) + "\n")

    result = tinyBuild(imageName)
    file.write("tiny build, " + str(result["build"]) + ", " + str(result["lifecycle"]) + ", " +
               str(result["fetchBuilder"]) + ", " + str(result["fetchBuildpack"]) + "\n")

    result = neverBuild(imageName)
    file.write("never policy build, " + str(result["build"]) + ", " + str(result["lifecycle"]) + ", " +
               str(result["fetchBuilder"]) + ", " + str(result["fetchBuildpack"]) + "\n")

    result = alwaysBuild(imageName)
    file.write("always policy build, " + str(result["build"]) + ", " + str(result["lifecycle"]) + ", " +
               str(result["fetchBuilder"]) + ", " + str(result["fetchBuildpack"]) + "\n")

    file.close()


if __name__ == "__main__":
    main()
