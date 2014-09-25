Feature: Host directories should be created as needed
    In order to simplify the setup of a backup routine
    As a system administrator
    I shouldn't need to create the directories for each hosts

    Scenario: The host directory does not exist in the destination directory
        Given the test_host directory does not exist
        When I invoke backup without parameters
        Then the program should exit 0
        And the test_host directory should contain 1 hourly snapshots

    Scenario: The destination directory does not exist
        Given the destination directory does not exist
        When I invoke backup without parameters
        Then the program should exit 1
        And I should see "does not exist"
