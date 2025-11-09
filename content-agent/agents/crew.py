from crewai import Agent, Task, Crew, Process
from langchain_google_genai import ChatGoogleGenerativeAI
from agents.llm_wrappers import GeminiLLM, ZAILLM
import os
import json

class ContentCrew:
    def __init__(self, user_preferences, schedule_params):
        self.user_preferences = user_preferences
        self.schedule_params = schedule_params
        self.llm = self._get_llm()
        self._create_agents()
        self._create_tasks()
        self.crew = Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )

    def _get_llm(self):
        # Configure based on user's preferred LLM
        core_agent_type = os.getenv("CORE_AGENT_TYPE", "gemini")
        print(f"Initializing LLM with type: {core_agent_type}")

        if core_agent_type == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable is not set")
            return GeminiLLM(api_key=api_key, model_name="gemini-2.0-flash-exp")
        elif core_agent_type == "zai":
            api_key = os.getenv("ZAI_API_KEY")
            if not api_key:
                raise ValueError("ZAI_API_KEY environment variable is not set")
            return ZAILLM(api_key=api_key)
        else:
            raise ValueError("Unsupported CORE_AGENT_TYPE. Use 'gemini' or 'zai'.")

    def _create_agents(self):
        # Define all the specialized agents using the custom LLM
        # Add model attribute for CrewAI compatibility
        model_identifier = getattr(self.llm, 'model_identifier', 'gemini-2.0-flash-exp')

        # Ensure model_identifier is not empty
        if not model_identifier or model_identifier.strip() == "":
            model_identifier = "gemini-2.0-flash-exp"

        print(f"Using model identifier: {model_identifier}")
        print(f"LLM type: {type(self.llm)}")

        self.trend_researcher = Agent(
            role='Trend Research Specialist',
            goal='Identify the most relevant and engaging trends in the user\'s niche',
            backstory="""You are an expert in digital trends and social media analytics.
            You have a keen eye for identifying emerging topics that will resonate
            with specific audiences.""",
            llm=self.llm,
            verbose=True,
            allow_delegation=False,
            tools=[]  # Add tools if needed
        )

        self.content_planner = Agent(
            role='Content Strategy Specialist',
            goal='Create compelling content plans based on trends and user preferences',
            backstory="""You are a creative content strategist with expertise in crafting
            engaging posts that drive interaction. You understand how to balance
            promotional content with value-driven posts.""",
            llm=self.llm,
            verbose=True,
            allow_delegation=False,
            tools=[]  # Add tools if needed
        )

        self.image_generator = Agent(
            role='Visual Content Creator',
            goal='Generate stunning images that complement the content',
            backstory="""You are a visual artist with deep understanding of image generation
            AI models. You know how to craft the perfect prompts to create images
            that capture attention and convey the right message.""",
            llm=self.llm,
            verbose=True,
            allow_delegation=False,
            tools=[]  # Add tools if needed
        )

        self.social_media_manager = Agent(
            role='Social Media Manager',
            goal='Organize and prepare content for posting according to the user-specified schedule',
            backstory="""You are a social media expert who excels at organizing content for optimal engagement
            within predefined scheduling constraints. You understand how to structure posts, optimize formatting,
            and prepare content that will be published at specific intervals determined by the user.""",
            llm=self.llm,
            verbose=True,
            allow_delegation=False,
            tools=[]  # Add tools if needed
        )

        self.agents = [self.trend_researcher, self.content_planner,
                      self.image_generator, self.social_media_manager]

    def _create_tasks(self):
        # Define the sequence of tasks
        self.research_task = Task(
            description=f"""Research current trends relevant to the user's niche: {self.user_preferences['niche']}.
            Focus on topics that align with these keywords: {self.user_preferences['keywords']}.
            Identify at least 5 trending topics with high engagement potential.
            Output should be a structured list of trends with brief explanations.""",
            agent=self.trend_researcher,
            expected_output="A structured list of 5+ trending topics with explanations."
        )

        self.plan_task = Task(
            description="""Based on the trend research, create a content plan for the next posts.
            For each post, include:
            1. An engaging caption
            2. Relevant hashtags
            3. Keywords for optimization
            4. A concept for the accompanying image
            5. The best timing for posting

            Format your response as a JSON array of post objects.""",
            agent=self.content_planner,
            expected_output="A JSON array of post objects with captions, hashtags, keywords, image concepts, and timing."
        )

        self.image_task = Task(
            description="""For each content plan item, create detailed prompts for image generation.
            The prompts should be optimized for the Replicate ideogram-v3-turbo model.
            Include style, composition, and other visual elements.

            Format your response as a JSON array matching the content plan, with each object containing an 'image_prompt' field.""",
            agent=self.image_generator,
            expected_output="A JSON array matching the content plan, with detailed image prompts for each post."
        )

        self.schedule_task = Task(
            description=f"""Create a detailed content organization plan based on these user-defined parameters: {self.schedule_params}.

            The user has specified exactly when and how often content should be posted. Your role is to:
            1. Organize the content in the correct sequence for posting
            2. Ensure each post is properly formatted for the platform
            3. Add any engagement optimization elements (like call-to-actions, questions, etc.)
            4. Structure the content to maintain consistency throughout the posting schedule

            Format your response as a JSON array where each object contains:
            - post_number: The sequence number of the post
            - caption: The formatted caption
            - hashtags: Relevant hashtags
            - image_prompt: The prompt for image generation
            - engagement_elements: Any specific engagement boosters for this post

            Do not modify the timing - focus solely on optimizing the content for the schedule the user has defined.""",
            agent=self.social_media_manager,
            expected_output="A JSON array of posts organized in sequence, with each post properly formatted for maximum engagement within the user-defined schedule."
         )

        self.tasks = [self.research_task, self.plan_task, self.image_task, self.schedule_task]

    def run(self):
        """Execute the crew to generate the complete content strategy"""
        return self.crew.kickoff()