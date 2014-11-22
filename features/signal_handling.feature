Feature: Clean exits when killed
    In order to stop a running backup
    As a system administrator
    I should be able to kill the process and not have to cleanup manually

    @wip
    Scenario: SIGTERM
        Given backup was invoked without parameters
        When I kill the process
        Then the program should exit 1
        And I should see "Signal 15 received"
