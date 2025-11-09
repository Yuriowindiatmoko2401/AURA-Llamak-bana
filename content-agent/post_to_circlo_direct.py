#!/usr/bin/env python3
"""
Direct posting script to post all 15 generated content items to getcirclo.com
"""

import requests
import json
import time

def post_content_directly():
    """Post all 15 content items directly to getcirclo.com via the new API endpoint"""

    print("🚀 Starting direct posting to getcirclo.com...")

    # The 15 content items from your schedule
    content_plan = [
        {
            "post_number": 1,
            "caption": "Kicking off the hour with a moment of calm. ✨ There's something so therapeutic about a clean space and a clear mind. What's one thing you do to get ready for a new week? Let me know below! 👇",
            "hashtags": ["#SundayReset", "#CleanWithMe", "#ASMRCleaning", "#CozyHome", "#WeeklyReset", "#SelfCareSunday", "#AestheticVibes", "#MindfulMoments"],
            "image_prompt": "cinematic photography, a serene and peaceful moment, a close-up shot focusing on a person's hands lighting a minimalist white candle on a wooden coffee table. The background is a tidy, cozy living room with a soft, neatly folded beige blanket and a vibrant green houseplant in soft focus. The scene is illuminated by bright, gentle natural light from a window, creating a warm and inviting atmosphere. shallow depth of field, photorealistic, calm aesthetic, Sunday reset vibe.",
            "engagement_elements": {"type": "Open Question", "prompt": "What's one thing you do to get ready for a new week?"},
            "image_url": "https://replicate.delivery/xezq/pfdjwleeweBatQ8TKeSfiMFtaYk0GZWMUlyd3xePduXWvtwzKA/tmpyo6is6pt.png",
            "image_status": "success"
        },
        {
            "post_number": 2,
            "caption": "Core memory UNLOCKED. 🔓 Remember begging your parents for these at the grocery store? If you could bring back ONE snack from the 2000s, what would it be? I'm team Dunkaroos all the way. 😂",
            "hashtags": ["#Y2K", "#2000sNostalgia", "#90sKid", "#ChildhoodMemories", "#CoreMemory", "#Throwback", "#RetroSnacks", "#TBT"],
            "image_prompt": "vibrant product flat lay photography, an energetic and colorful composition of nostalgic Y2K snacks including Dunkaroos, 3D Doritos, and Trix Yogurt. The snacks are artfully arranged on a shimmering, slightly holographic surface. Bright, high-contrast studio lighting makes the retro packaging colors pop. Y2K aesthetic, playful, hyper-realistic, sharp focus, saturated colors.",
            "engagement_elements": {"type": "Nostalgia Bait Question", "prompt": "If you could bring back ONE snack from the 2000s, what would it be?"},
            "image_url": "https://replicate.delivery/xezq/RJJw8JjhlkLNEdgCm1nbhwlyQg96sIH3U9oWfxZnnz7ztwzKA/tmp3xrg9v5p.png",
            "image_status": "success"
        },
        {
            "post_number": 3,
            "caption": "Mind-blowing AI tool you need to try NOW. 🤯 I asked the new ChatGPT-4o to plan my entire weekend trip in a conversational voice chat, from restaurants to hidden gems. The future is officially here. Are you excited or nervous about how fast AI is evolving? Sound off in the comments! 🤖",
            "hashtags": ["#AI", "#ArtificialIntelligence", "#ChatGPT4o", "#TechTrends", "#FutureTech", "#Innovation", "#ProductivityHacks", "#AITools"],
            "image_prompt": "futuristic digital art, a smartphone angled dynamically, displaying a sleek AI chat interface with a travel itinerary. Glowing, holographic icons of famous landmarks, food, and airplanes float out of the screen, creating a sense of depth and interaction. The background is a dark, sophisticated gradient with glowing blue and purple light trails. tech concept art, vibrant illustration, neon glow, innovative technology theme.",
            "engagement_elements": {"type": "Debate Starter", "prompt": "Are you excited or nervous about how fast AI is evolving?"},
            "image_url": "https://replicate.delivery/xezq/T49EJWyKHoKuFhVRf2Zb2WWokLmwu1qMN7lk7F8N5wG4twzKA/tmpbgpryx3a.png",
            "image_status": "success"
        },
        {
            "post_number": 4,
            "caption": "Your daily reminder to romanticize the small moments. 🌿 Swapping my afternoon doom-scroll for a cup of tea and 10 minutes of quiet. You don't need a huge budget or a full day off to practice self-care. Save this for when you need a moment of peace. 🤍",
            "hashtags": ["#SoftLiving", "#Mindfulness", "#SimplePleasures", "#SelfCareTips", "#DigitalDetox", "#CozyVibes", "#MentalWellness", "#SlowLiving"],
            "image_prompt": "cinematic still photography, an intimate close-up shot capturing a mindful moment. Wisps of delicate steam rise from a beautiful, handmade ceramic mug as tea is poured into it. The scene is bathed in warm, soft golden hour sunlight that streams through a window, highlighting the steam. In the soft-focus background, an open book rests on a wooden table beside a small potted plant. photorealistic, soft living aesthetic, cozy and serene atmosphere, shallow depth of field, warm color palette.",
            "engagement_elements": {"type": "Call to Action", "prompt": "Save this for when you need a moment of peace."},
            "image_url": "https://replicate.delivery/xezq/joifJq0GdEX0ZKCltq8eeGkVBCeYadAdBwvyfa5zby9UfW4ZF/tmptl0sujdj.png",
            "image_status": "success"
        },
        {
            "post_number": 5,
            "caption": "Let's be real for a second. 👀 I bought the viral [Product Name] so you don't have to. Here's my 100% honest review on why it's NOT worth the hype. Let's normalize not buying everything we see online. What's a viral product that disappointed you? Let's talk about it! #Deinfluencing",
            "hashtags": ["#Deinfluencing", "#HonestReview", "#NotWorthTheHype", "#AntiHaul", "#SaveYourMoney", "#ViralProducts", "#Consumerism", "#RadicalHonesty"],
            "image_prompt": "candid portrait photography, a medium close-up of a person with a genuine and relatable expression, looking directly into the camera. They are holding up a generic beauty product with a skeptical, questioning look on their face. The lighting is natural and even, creating an authentic, non-studio feel. The background is simple and uncluttered. photorealistic, honest review aesthetic.",
            "engagement_elements": {"type": "Shared Experience Question", "prompt": "What's a viral product that disappointed you?"},
            "image_url": "https://replicate.delivery/xezq/coBzCXNdMGYlApfZLKD6HARAEdzy0gIi7Vow2dsViJPCuwzKA/tmpepkd7bys.png",
            "image_status": "success"
        },
        {
            "post_number": 6,
            "caption": "Ever wonder why so many fast-food logos are red and yellow? 🤔 It's not a coincidence – it's psychology! 🧠 Dive into the fascinating 'ketchup and mustard theory' with me. You'll never look at a burger joint the same way again. What niche topic should I cover next?",
            "hashtags": ["#FunFacts", "#DidYouKnow", "#MarketingPsychology", "#ColorTheory", "#DeepDive", "#LearnOnInstagram", "#BrandStrategy", "#Curiosity"],
            "image_prompt": "conceptual graphic illustration, a stylized human brain is the central focus. One half of the brain is depicted as a delicious, photorealistic cheeseburger, while the other half is a clean, abstract diagram showing a color wheel and psychological icons. Artistic splatters of vibrant red ketchup and bright yellow mustard surround the central image on a clean white background. modern graphic design.",
            "engagement_elements": {"type": "Content Request", "prompt": "What niche topic should I cover next?"},
            "image_url": "https://replicate.delivery/xezq/nZNSWMLrJsanAVMr2Tq2TKUFp2SlLfgxsRWxNHRFSeGPchnVA/tmpyekpr8l2.png",
            "image_status": "success"
        },
        {
            "post_number": 7,
            "caption": "The most important 5 minutes of my morning. ☕️ There's a certain magic to the first coffee of the day. How do you take yours? Black, cream, sugar? Spill the beans in the comments!",
            "hashtags": ["#MorningRoutine", "#CoffeeLover", "#MicroVlog", "#Aesthetic", "#SimplePleasures", "#GRWM", "#DayInTheLife", "#CoffeeTime"],
            "image_prompt": "aesthetic lifestyle photography, an overhead shot (flat lay) of a freshly brewed pour-over coffee being poured into a ceramic mug. The scene includes a bag of artisanal coffee beans, a small milk pitcher, and a croissant on a rustic wooden board. Soft morning light illuminates the scene, creating long, gentle shadows. photorealistic, cozy morning vibe.",
            "engagement_elements": {"type": "Simple Preference Question", "prompt": "How do you take your coffee? Black, cream, sugar?"},
            "image_url": "https://replicate.delivery/xezq/j9ufK6H2nCXeqElURqsNWCgYhpxsJXGmY1WqpEXhbWNYchnVA/tmpxf_my9ik.png",
            "image_status": "success"
        },
        {
            "post_number": 8,
            "caption": "Saturday morning cartoons just hit different. 📺 Waking up early, bowl of cereal in hand... pure bliss. If you had a time machine, which cartoon would you watch first? My vote is for Recess!",
            "hashtags": ["#90sCartoons", "#Nostalgia", "#SaturdayMorning", "#Childhood", "#CoreMemory", "#Throwback", "#2000sKid", "#SimplerTimes"],
            "image_prompt": "retro illustration, a vibrant and stylized scene of a kid in pajamas sitting cross-legged on a shag carpet, holding a bowl of colorful cereal. They are mesmerized by an old, boxy CRT television that is glowing with the colors of a cartoon. The style should evoke 90s animation, with bold lines and bright, flat colors. nostalgic, playful.",
            "engagement_elements": {"type": "Hypothetical Question", "prompt": "If you had a time machine, which cartoon would you watch first?"},
            "image_url": "https://replicate.delivery/xezq/Uj0MJaWhg8qXANWaw3IrYhAeJRxNcoRJNuGIbAbVH8kQuwzKA/tmpxrynwkdw.png",
            "image_status": "success"
        },
        {
            "post_number": 9,
            "caption": "I asked an AI to redesign my bedroom and the results are WILD. 🤖 Swipe to see the 3 concepts it generated based on my prompts. Which one is your favorite: 'Cyberpunk Loft,' 'Forest Sanctuary,' or 'Minimalist Cloud'? Let me know!",
            "hashtags": ["#AIart", "#Midjourney", "#InteriorDesign", "#FutureHome", "#AItools", "#CreativeTech", "#ConceptArt", "#HomeDecor"],
            "image_prompt": "digital art, a triptych showing three distinct interior design concepts for a single bedroom, generated by AI. The first is a neon-lit cyberpunk style, the second is filled with plants and natural wood, the third is all-white, minimalist, and ethereal. The images are hyper-realistic, showcasing the power of AI image generation. futuristic, design inspiration.",
            "engagement_elements": {"type": "Vote/Poll", "prompt": "Which one is your favorite: 'Cyberpunk Loft,' 'Forest Sanctuary,' or 'Minimalist Cloud'?"},
            "image_url": "https://replicate.delivery/xezq/HqSXSYPsin4DI51Uqb10XtOxkJtdPbpcRSeqUWcWCLGWuwzKA/tmp0gznp7cf.png",
            "image_status": "success"
        },
        {
            "post_number": 10,
            "caption": "Inhale peace, exhale stress. 🧘‍♀️ My favorite way to reset during a busy day is 5 minutes of mindful journaling. Here's a prompt for you: 'What is one thing that made you smile today?' Share yours if you feel comfortable. 🤍 #SoftLiving",
            "hashtags": ["#Journaling", "#MindfulMoments", "#MentalWellness", "#SelfCare", "#SlowLiving", "#Gratitude", "#PositiveVibes", "#TakeABreak"],
            "image_prompt": "calm lifestyle photography, a person's hands are shown writing in a beautiful, open journal with a stylish pen. Next to the journal is a steaming mug of herbal tea on a clean, white desk. The lighting is soft and natural. The focus is on the act of writing and the peaceful atmosphere. photorealistic, serene, inspirational.",
            "engagement_elements": {"type": "Inspirational Prompt", "prompt": "Share one thing that made you smile today in the comments."},
            "image_url": "https://replicate.delivery/xezq/Tp0cIZvHbsJrL1gqhISXHqj5INDMmGNop26jo9WpFPnNX4ZF/tmpcl9hv2fp.png",
            "image_status": "success"
        },
        {
            "post_number": 11,
            "caption": "Let's talk about viral 'hacks' that are actually just... a waste of time. 🚫 I tried 3 of the most popular ones so you don't have to. Spoiler: they didn't work. What's the worst 'hack' you've ever tried? Let's save each other some time and energy!",
            "hashtags": ["#Deinfluencing", "#LifeHacks", "#MythBusting", "#HonestReview", "#RealityCheck", "#SaveYourTime", "#AntiHaul", "#Truth"],
            "image_prompt": "candid photography, a slightly humorous and exasperated-looking person is in their kitchen, surrounded by the messy aftermath of a failed 'kitchen hack'. For example, a failed attempt at a viral recipe. The lighting is bright and realistic, capturing a genuine moment of 'this did not work'. relatable, funny, authentic.",
            "engagement_elements": {"type": "Community Warning/Shared Experience", "prompt": "What's the worst 'hack' you've ever tried?"},
            "image_url": "https://replicate.delivery/xezq/u2J9vssDF342BtobLDAEjksP4iA9eyvk6xbwBoPSzj2fchnVA/tmpgea3isn_.png",
            "image_status": "success"
        },
        {
            "post_number": 12,
            "caption": "You click it every day, but do you know what it is? 🤔 The 'save' icon is a floppy disk! Let's take a quick dive into this piece of 'fossil tech' that's still a huge part of our digital lives. What other modern icon has a strange origin story?",
            "hashtags": ["#TechHistory", "#DidYouKnow", "#FunFacts", "#DeepDive", "#RetroTech", "#LearnSomethingNew", "#Curiosity", "#UIUX"],
            "image_prompt": "conceptual art, a large, photorealistic 3.5-inch floppy disk is shown cracking open, and from the inside, a glowing, modern digital 'save' icon emerges. The background is a blueprint-style grid, hinting at design and history. The image perfectly blends retro and modern technology. creative, educational, high detail.",
            "engagement_elements": {"type": "Curiosity-driven Question", "prompt": "What other modern icon has a strange origin story?"},
            "image_url": "https://replicate.delivery/xezq/B1AtJbrnGcZsONg70eDhWbWkNZjcgCoUiUjJBjDkKdJkuwzKA/tmpaep55329.png",
            "image_status": "success"
        },
        {
            "post_number": 13,
            "caption": "A mini-vlog of 'What's In My Bag?' 👜 The essentials for a day on the go. My can't-live-without item is definitely my portable charger. What's the one thing you NEVER leave the house without?",
            "hashtags": ["#WhatsInMyBag", "#EverydayCarry", "#BagSpill", "#MicroVlog", "#Essentials", "#DayInTheLife", "#OnTheGo", "#Aesthetic"],
            "image_prompt": "aesthetic flat lay photography, the contents of a stylish tote bag are artfully arranged on a neutral-colored surface. Items include a phone, wallet, keys, lipstick, a book, and a portable charger. The composition is balanced and visually pleasing. The lighting is bright and clean. photorealistic, organized, lifestyle.",
            "engagement_elements": {"type": "Direct Question", "prompt": "What's the one thing you NEVER leave the house without?"},
            "image_url": "https://replicate.delivery/xezq/w5n8SeevfbTjsJry2UHIvJI4JXXRogecs27HDUPAk4rF1FesC/tmppwhivcga.png",
            "image_status": "success"
        },
        {
            "post_number": 14,
            "caption": "If you can hear this image, we're officially friends. 🔊 That dial-up internet sound was the soundtrack to the 90s. What sound instantly takes you back to your childhood? The Blockbuster video case snapping shut? A specific video game sound?",
            "hashtags": ["#NostalgicSounds", "#90sKid", "#DialUp", "#TheSoundOfMyChildhood", "#Throwback", "#CoreMemory", "#Retro", "#IfYouKnowYouKnow"],
            "image_prompt": "vintage tech photo, a close-up shot of an old, beige desktop computer modem from the 1990s with its lights blinking. The photo has a slightly grainy, film-like quality to enhance the retro feel. In the background, a classic CRT monitor is softly out of focus. nostalgic, atmospheric, detailed.",
            "engagement_elements": {"type": "Sensory Memory Question", "prompt": "What sound instantly takes you back to your childhood?"},
            "image_url": "https://replicate.delivery/xezq/5ZBTWNe8Nyy9BSqffXGL5OZ1t2QewkfbYKMvtffNHw20tuwzKA/tmpqbi5ujg8.png",
            "image_status": "success"
        },
        {
            "post_number": 15,
            "caption": "Final post of the hour! I ran an experiment: Can AI write a better caption than a human? Caption A is mine, Caption B is from AI. Read them both in the image and vote for the winner in the comments! Who will win: Human or Machine? 🤖 vs. 👩‍💻",
            "hashtags": ["#AIvsHuman", "#SocialMediaExperiment", "#ChatGPT", "#AI", "#ContentCreation", "#TechTrends", "#VoteNow", "#FutureOfContent"],
            "image_prompt": "clean graphic design, a split-screen image for social media. The left side is labeled 'Caption A: Human' and the right side 'Caption B: AI'. Both sides feature the same photo of a sunset, but with different caption text below their respective labels. The design is modern, using bold, clear fonts and a simple color scheme to encourage reading and comparison.",
            "engagement_elements": {"type": "Interactive Poll/Vote", "prompt": "Vote for the winner in the comments: A or B?"},
            "image_url": "https://replicate.delivery/xezq/YTYFevzJ4N0QZKZfN1J7gSDLNQfidu1ZTwISIeQoaooW2FesC/tmp3rjdt_my.png",
            "image_status": "success"
        }
    ]

    # Prepare the request payload
    payload = {
        "content_plan": content_plan,
        "user_preferences": {
            "niche": "general",
            "profile_type": "general"
        },
        "delay_seconds": 15  # 15 seconds between posts to avoid rate limiting
    }

    print(f"📋 Posting {len(content_plan)} content items to getcirclo.com...")
    print(f"⏱️  15 second delay between posts to avoid rate limiting")
    print(f"🎯 Estimated total time: {len(content_plan) * 15 / 60:.1f} minutes")

    try:
        # Make the request to our new direct posting endpoint
        response = requests.post(
            "http://localhost:8000/post-direct",
            json=payload,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            result = response.json()
            print(f"\n🎉 POSTING COMPLETED!")
            print(f"📊 Results:")
            print(f"   Total posts: {result.get('total_posts', 0)}")
            print(f"   ✅ Successful: {result.get('successful_posts', 0)}")
            print(f"   ❌ Failed: {result.get('failed_posts', 0)}")
            print(f"   📈 Success rate: {result.get('success_rate', 0):.1f}%")

            print(f"\n🔍 Detailed results:")
            for post_result in result.get('results', []):
                status_emoji = "✅" if post_result.get('status') == 'success' else "❌"
                print(f"   {status_emoji} Post {post_result.get('post_number')}: {post_result.get('caption_preview', 'N/A')}...")
                if post_result.get('status') == 'failed':
                    print(f"      Error: {post_result.get('error', 'Unknown error')}")

            print(f"\n🌐 Check your posts on getcirclo.com!")
            print(f"   They should appear on your profile shortly.")

        else:
            print(f"❌ ERROR: Request failed with status {response.status_code}")
            print(f"Response: {response.text}")

    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Could not connect to the server.")
        print("   Make sure the content agent is running on http://localhost:8000")
        print("   Start it with: python main.py")
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")

if __name__ == "__main__":
    post_content_directly()